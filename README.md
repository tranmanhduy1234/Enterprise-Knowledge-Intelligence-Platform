Cách khởi chạy hệ thống

'''
docker-compose up -d
celery -A app.workers.celery_app worker --loglevel=info -P solo (chạy terminal riêng)
python -m run
'''