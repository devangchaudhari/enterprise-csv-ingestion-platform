from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from backend.app.core.database import SessionLocal
from backend.app.models.schema_models import IngestionJob
from backend.app.services.job_executor import JobExecutor

scheduler = BackgroundScheduler()

def scheduled_job_runner(job_id: str):
    db = SessionLocal()
    try:
        JobExecutor.execute_job(db, job_id, execution_type="Scheduled")
    finally:
        db.close()

class SchedulerService:
    @staticmethod
    def start():
        if not scheduler.running:
            scheduler.start()
            SchedulerService.sync_jobs()

    @staticmethod
    def sync_jobs():
        scheduler.remove_all_jobs()
        db = SessionLocal()
        try:
            active_jobs = db.query(IngestionJob).filter(
                IngestionJob.is_active == True,
                IngestionJob.schedule_type != "manual"
            ).all()

            for job in active_jobs:
                SchedulerService.register_job(job)
        finally:
            db.close()

    @staticmethod
    def register_job(job: IngestionJob):
        job_id_str = f"job_{job.id}"
        if scheduler.get_job(job_id_str):
            scheduler.remove_job(job_id_str)

        if not job.is_active or job.schedule_type == "manual":
            return

        trigger = None
        if job.schedule_type == "hourly":
            trigger = IntervalTrigger(hours=1)
        elif job.schedule_type == "daily":
            trigger = IntervalTrigger(days=1)
        elif job.schedule_type == "custom_cron" and job.schedule_value:
            try:
                parts = job.schedule_value.split()
                if len(parts) == 5:
                    trigger = CronTrigger.from_crontab(job.schedule_value)
            except Exception:
                trigger = IntervalTrigger(hours=24)

        if trigger:
            scheduler.add_job(
                scheduled_job_runner,
                trigger=trigger,
                args=[job.id],
                id=job_id_str,
                name=job.name,
                replace_existing=True
            )
