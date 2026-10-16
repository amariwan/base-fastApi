from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

from app.core.core_messages import MessageKeys, msg
from fastapi import APIRouter, FastAPI

StartupHook = Callable[[FastAPI], Awaitable[object] | object]
ShutdownHook = Callable[[FastAPI, object], Awaitable[None] | None]
logger = logging.getLogger("app_logger")


@dataclass(frozen=True)
class ServiceRegistration:
    name: str
    routers: list[APIRouter] = field(default_factory=list)
    startup_hooks: list[StartupHook] = field(default_factory=list)
    shutdown_hooks: list[ShutdownHook] = field(default_factory=list)
    runtime_config_hook: Callable[[], Mapping[str, object]] | None = None
    use_api_prefix: bool = True


@dataclass(frozen=True)
class RuntimeService:
    registration: ServiceRegistration
    startup_results: list[object] = field(default_factory=list)


def discover_service_module_names(services_dir: Path | None = None) -> list[str]:
    resolved_services_dir = services_dir or (Path(__file__).resolve().parents[2] / "services")
    if not resolved_services_dir.is_dir():
        return []

    module_names: list[str] = []
    for service_dir in resolved_services_dir.iterdir():
        if not service_dir.is_dir() or service_dir.name.startswith("_"):
            continue
        integration_file = service_dir / "integration.py"
        if integration_file.is_file():
            module_names.append(f"app.services.{service_dir.name}.integration")
    return sorted(module_names)


async def _maybe_await(value: object) -> object:
    # Background tasks returned by startup hooks must not be awaited here.
    # They are kept as startup results so shutdown hooks can cancel/await them.
    if isinstance(value, (asyncio.Task, asyncio.Future)):
        return value
    if inspect.isawaitable(value):
        return await value
    return value


def _coerce_registration(module_name: str, payload: object) -> ServiceRegistration:
    if isinstance(payload, ServiceRegistration):
        return payload
    if not isinstance(payload, dict):
        raise TypeError(f"{module_name}.register_service() must return dict or ServiceRegistration")

    name = payload.get("name", module_name)
    routers = payload.get("routers", [])
    startup_hooks = payload.get("startup", [])
    shutdown_hooks = payload.get("shutdown", [])
    runtime_config_hook = payload.get("runtime_config")
    use_api_prefix = payload.get("use_api_prefix", True)

    if not isinstance(routers, list) or not all(isinstance(router, APIRouter) for router in routers):
        raise TypeError(f"{module_name}.register_service().routers must be list[APIRouter]")
    if not isinstance(startup_hooks, list) or not all(callable(h) for h in startup_hooks):
        raise TypeError(f"{module_name}.register_service().startup must be list[callable]")
    if not isinstance(shutdown_hooks, list) or not all(callable(h) for h in shutdown_hooks):
        raise TypeError(f"{module_name}.register_service().shutdown must be list[callable]")
    if runtime_config_hook is not None and not callable(runtime_config_hook):
        raise TypeError(f"{module_name}.register_service().runtime_config must be callable")
    if not isinstance(use_api_prefix, bool):
        raise TypeError(f"{module_name}.register_service().use_api_prefix must be bool")

    return ServiceRegistration(
        name=name,
        routers=routers,
        startup_hooks=startup_hooks,
        shutdown_hooks=shutdown_hooks,
        runtime_config_hook=runtime_config_hook,
        use_api_prefix=use_api_prefix,
    )


def load_service_registrations(module_names: list[str]) -> list[ServiceRegistration]:
    registrations: list[ServiceRegistration] = []
    for module_name in module_names:
        try:
            module = import_module(module_name)
        except Exception as exc:
            logger.warning(msg.get(MessageKeys.EXTENSIONS_SKIP_MODULE, module=module_name, error=exc))
            continue
        register_service = getattr(module, "register_service", None)
        if not callable(register_service):
            logger.warning(msg.get(MessageKeys.EXTENSIONS_REGISTER_SERVICE_MISSING, module=module_name))
            continue
        try:
            payload = register_service()
            registrations.append(_coerce_registration(module_name, payload))
        except Exception as exc:
            logger.warning(msg.get(MessageKeys.EXTENSIONS_REGISTER_SERVICE_FAILED, module=module_name, error=exc))
            continue
    return registrations


def get_service_registrations() -> list[ServiceRegistration]:
    module_names = discover_service_module_names()
    if not module_names:
        raise RuntimeError(msg.get(MessageKeys.EXTENSIONS_NO_INTEGRATION_MODULES))

    registrations = load_service_registrations(module_names)
    if not registrations:
        modules = ", ".join(module_names)
        raise RuntimeError(msg.get(MessageKeys.EXTENSIONS_NO_VALID_REGISTRATIONS, modules=modules))
    for registration in registrations:
        if not registration.routers:
            raise RuntimeError(msg.get(MessageKeys.EXTENSIONS_NO_ROUTERS_CONFIGURED, service=registration.name))
    return registrations


def register_service_routers(app: FastAPI, api_prefix: str, registrations: list[ServiceRegistration]) -> None:
    for registration in registrations:
        for router in registration.routers:
            if registration.use_api_prefix:
                app.include_router(router, prefix=api_prefix)
            else:
                app.include_router(router)


async def run_service_startup(app: FastAPI, registrations: list[ServiceRegistration]) -> list[RuntimeService]:
    runtime_services: list[RuntimeService] = []
    for registration in registrations:
        results: list[object] = []
        for startup_hook in registration.startup_hooks:
            results.append(await _maybe_await(startup_hook(app)))
        runtime_services.append(RuntimeService(registration=registration, startup_results=results))
    return runtime_services


async def run_service_shutdown(app: FastAPI, runtime_services: list[RuntimeService]) -> None:
    for runtime_service in reversed(runtime_services):
        hooks = runtime_service.registration.shutdown_hooks
        if not hooks:
            continue
        for idx in range(len(hooks) - 1, -1, -1):
            shutdown_hook = hooks[idx]
            startup_result = (
                runtime_service.startup_results[idx] if idx < len(runtime_service.startup_results) else None
            )
            try:
                await _maybe_await(shutdown_hook(app, startup_result))
            except Exception:
                logger.exception(
                    "Shutdown hook failed for service '%s' (hook index %s)",
                    runtime_service.registration.name,
                    idx,
                )
