from django.db import migrations


def migrate_existing_catalog(apps, schema_editor):
    Category = apps.get_model('services', 'ServiceCategory')
    ClientType = apps.get_model('services', 'ClientType')
    Service = apps.get_model('services', 'Service')
    for category in Category.objects.all():
        client_type, _ = ClientType.objects.get_or_create(slug=category.slug, defaults={
            'name': category.name, 'description': category.description,
            'is_active': category.is_active, 'sort_order': category.display_order,
        })
        for service in Service.objects.filter(category=category):
            service.client_types.add(client_type)


class Migration(migrations.Migration):
    dependencies = [('services', '0003_clienttype_hairstyleoptiongroup_service_client_types_and_more')]
    operations = [migrations.RunPython(migrate_existing_catalog, migrations.RunPython.noop)]
