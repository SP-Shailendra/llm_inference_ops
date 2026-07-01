from fastapi import APIRouter, HTTPException

from app.core.benchmark_engine import benchmark_engine
from app.db.session import benchmark_db
from app.schemas.benchmark import BenchmarkJob, BenchmarkRunRequest

router = APIRouter()


@router.post("/run", response_model=BenchmarkJob, summary="Run benchmark job")
async def run_benchmark(request: BenchmarkRunRequest):
    try:
        return await benchmark_engine.run(request)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Benchmark run failed: {str(ex)}") from ex


@router.get("/jobs", summary="List benchmark jobs")
async def list_benchmark_jobs():
    return {"jobs": benchmark_db.list_jobs()}


@router.get("/jobs/{job_id}", response_model=BenchmarkJob, summary="Get benchmark job")
async def get_benchmark_job(job_id: str):
    job = benchmark_db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Benchmark job not found")
    return job
