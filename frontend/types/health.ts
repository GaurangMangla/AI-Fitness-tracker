export interface HealthStatus {
  status: "ok" | "degraded";
  version: string;
  database: "healthy" | "unhealthy";
}
