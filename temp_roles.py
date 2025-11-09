import os, sys
sys.path.append('src')
from core.auth.settings import RoleSettings
os.environ['ROLE_ACTIVE'] = 'true'
os.environ['ROLE_ADMIN_ROLES'] = '["admin"]'
os.environ['ROLE_READ_ROLES'] = '[]'
os.environ['ROLE_WRITE_ROLES'] = '[]'
os.environ['ROLE_DELETE_ROLES'] = '[]'
print(RoleSettings())
