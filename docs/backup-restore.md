# Backup e restore

Os scripts ficam em `src/opengeosgb/br/`.

```bash
geonode-docker exec django sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./opengeosgb/br/backup.sh $BKP_FOLDER_NAME'
geonode-docker exec django sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./opengeosgb/br/restore.sh $BKP_FOLDER_NAME'
```

- `BKP_FOLDER_NAME`: pasta compartilhada de backup, a partir da raiz (padrão `backup_restore`).
- `SOURCE_URL`: URL do servidor que gerou o backup.
- `TARGET_URL`: URL do servidor que vai ser sincronizado.
