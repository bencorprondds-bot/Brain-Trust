
import threading
import uuid
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class JobManager:
    """
    Manages background tasks using a thread pool.
    Stores job status and results in memory.
    """
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs = {}
        self.lock = threading.Lock()

    def submit_job(self, func, *args, **kwargs):
        """
        Submits a function to run in the background.
        Returns the job_id.
        """
        job_id = str(uuid.uuid4())
        
        with self.lock:
            self.jobs[job_id] = {
                'id': job_id,
                'status': 'queued',
                'submitted_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'result': None,
                'error': None,
                'logs': []
            }

        # Submit to executor
        self.executor.submit(self._run_job, job_id, func, *args, **kwargs)
        return job_id

    def _run_job(self, job_id, func, *args, **kwargs):
        """
        Internal wrapper to run the job and track status.
        """
        with self.lock:
            if job_id not in self.jobs:
                return
            self.jobs[job_id]['status'] = 'running'
            self.jobs[job_id]['started_at'] = datetime.now().isoformat()
            self.jobs[job_id]['logs'].append(f"Job started at {self.jobs[job_id]['started_at']}")

        try:
            # Run the actual function
            result = func(*args, **kwargs)
            
            with self.lock:
                self.jobs[job_id]['status'] = 'completed'
                self.jobs[job_id]['result'] = result
                self.jobs[job_id]['completed_at'] = datetime.now().isoformat()
                self.jobs[job_id]['logs'].append("Job completed successfully.")
                
        except Exception as e:
            with self.lock:
                self.jobs[job_id]['status'] = 'failed'
                self.jobs[job_id]['error'] = str(e)
                self.jobs[job_id]['completed_at'] = datetime.now().isoformat()
                self.jobs[job_id]['logs'].append(f"Error: {str(e)}")

    def get_job(self, job_id):
        """
        Get current status of a job.
        """
        with self.lock:
            return self.jobs.get(job_id)

    def list_jobs(self):
        """
        List all jobs (summary).
        """
        with self.lock:
            # Return a list of summaries
            return list(self.jobs.values())
