from organizations.models import *
from accounts.models import *

print(Organization.objects.all())
a = CustomUser.objects.all().last()
print(a.owned_organizations)
o  = Organization.objects.all()
print(o.owner)

no = Organization.objects.create(
    name = 'a is not owner',
    description = 'a is not owner',
    owner = CustomUser.objects.filter(username = 'nik').first()
)
no.users.add(a)