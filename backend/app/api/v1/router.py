"""Aggregates every router for API version 1."""

from fastapi import APIRouter

from app.api.v1.routers import auth, exercises, health, nutrition, progress, stats, users, workouts

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(exercises.router)
api_router.include_router(workouts.router)
api_router.include_router(stats.router)
api_router.include_router(progress.router)
api_router.include_router(nutrition.router)
