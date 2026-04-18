# File Uploads — Drive Catalog

Binaries (PDFs, images, videos, audio) uploaded through the app live in Google Drive under the folder **"Enriquez OS / Files"**. This file is the local index so Claude and Allen can find them without opening Drive.

Append-only table. App writes one row per upload.

| filename | drive_url | drive_id | tags | caption | uploaded |
|---|---|---|---|---|---|
