#!/bin/sh
# Готовит MinIO к работе бэкенда: бакет и отдельный пользователь с доступом только к нему.
# Root-учётка остаётся для консоли MinIO. Запуск повторяемый: уже созданное не ломается.
set -eu

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/$S3_BUCKET"

cat > /tmp/backend-policy.json <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::$S3_BUCKET/*"]
    }
  ]
}
POLICY
mc admin policy create local labka-backend /tmp/backend-policy.json
mc admin user add local "$S3_ACCESS_KEY" "$S3_SECRET_KEY"
# В образе MinIO нет grep: повторная привязка политики возвращает ошибку, её пропускаем.
mc admin policy attach local labka-backend --user "$S3_ACCESS_KEY" || true
