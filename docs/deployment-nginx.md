# Nginx Domain Proxy Notes

The public HTTPS domains are terminated by the host Nginx service on EC2.
These settings live outside the repository at `/etc/nginx/sites-available/stegano`,
so they are not changed by `git reset --hard origin/main` during application deploys.

## Required Upload Limit

Large mail attachments are uploaded through the API endpoint:

```text
https://api.stegano.app/scan
```

The `api.stegano.app` server block must include:

```nginx
client_max_body_size 50M;
```

Recommended shape:

```nginx
server {
    server_name api.stegano.app;

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/stegano.app/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/stegano.app/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}
```

The `mail.stegano.app` server block may also keep the same limit for consistency.

## Duplicate Config Warning

Do not keep backup config files inside `/etc/nginx/sites-enabled`.
Nginx loads every file in that directory, so backups such as this will cause
duplicate `server_name` warnings:

```text
/etc/nginx/sites-enabled/stegano.backup.*
```

Move backups outside the enabled config directory:

```bash
sudo mkdir -p /etc/nginx/backup
sudo mv /etc/nginx/sites-enabled/stegano.backup.* /etc/nginx/backup/
```

Verify and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```
