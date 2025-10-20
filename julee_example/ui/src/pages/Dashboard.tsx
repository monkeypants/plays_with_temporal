"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Database,
  Workflow,
  Clock,
  CheckCircle,
  AlertCircle,
  XCircle,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface SystemHealth {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  services: {
    api: "up" | "down";
    temporal: "up" | "down";
    storage: "up" | "down";
  };
}

interface DashboardStats {
  queries: {
    total: number;
    active: number;
    completed: number;
    failed: number;
  };
  specifications: {
    total: number;
    active: number;
    completed: number;
  };
  workflows: {
    running: number;
    completed: number;
    failed: number;
  };
}

export default function DashboardPage() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["system", "health"],
    queryFn: async (): Promise<SystemHealth> => {
      const response = await apiClient.get("/health");
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: async (): Promise<DashboardStats> => {
      // This would be replaced with actual API calls to your FastAPI endpoints
      const [queriesResponse, specsResponse] = await Promise.all([
        apiClient.get("/knowledge_service_queries?limit=1000"),
        apiClient.get("/assembly_specifications?limit=1000"),
      ]);

      const queries = queriesResponse.data.items || [];
      const specifications = specsResponse.data.items || [];

      return {
        queries: {
          total: queries.length,
          active: queries.filter((q: any) => q.status === "active").length,
          completed: queries.filter((q: any) => q.status === "completed")
            .length,
          failed: queries.filter((q: any) => q.status === "failed").length,
        },
        specifications: {
          total: specifications.length,
          active: specifications.filter((s: any) => s.status === "active")
            .length,
          completed: specifications.filter((s: any) => s.status === "completed")
            .length,
        },
        workflows: {
          running: 5, // Mock data - would come from Temporal API
          completed: 127,
          failed: 3,
        },
      };
    },
    refetchInterval: 60000, // Refresh every minute
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
      case "up":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "degraded":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case "unhealthy":
      case "down":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "healthy":
      case "up":
        return "default";
      case "degraded":
        return "secondary";
      case "unhealthy":
      case "down":
        return "destructive";
      default:
        return "outline";
    }
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your workflow system
        </p>
      </div>

      {/* System Health Section */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-foreground mb-4">
          System Health
        </h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {healthLoading ? (
            <>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    <Skeleton className="h-4 w-20" />
                  </CardTitle>
                  <Skeleton className="h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-6 w-16" />
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    <Skeleton className="h-4 w-16" />
                  </CardTitle>
                  <Skeleton className="h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-6 w-16" />
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    <Skeleton className="h-4 w-20" />
                  </CardTitle>
                  <Skeleton className="h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-6 w-16" />
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    <Skeleton className="h-4 w-16" />
                  </CardTitle>
                  <Skeleton className="h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-6 w-16" />
                </CardContent>
              </Card>
            </>
          ) : (
            <>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Overall Status
                  </CardTitle>
                  {getStatusIcon(health?.status || "unknown")}
                </CardHeader>
                <CardContent>
                  <Badge
                    variant={getStatusVariant(health?.status || "unknown")}
                  >
                    {health?.status || "Unknown"}
                  </Badge>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    API Service
                  </CardTitle>
                  {getStatusIcon(health?.services?.api || "unknown")}
                </CardHeader>
                <CardContent>
                  <Badge
                    variant={getStatusVariant(
                      health?.services?.api || "unknown",
                    )}
                  >
                    {health?.services?.api || "Unknown"}
                  </Badge>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Temporal
                  </CardTitle>
                  {getStatusIcon(health?.services?.temporal || "unknown")}
                </CardHeader>
                <CardContent>
                  <Badge
                    variant={getStatusVariant(
                      health?.services?.temporal || "unknown",
                    )}
                  >
                    {health?.services?.temporal || "Unknown"}
                  </Badge>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Storage</CardTitle>
                  {getStatusIcon(health?.services?.storage || "unknown")}
                </CardHeader>
                <CardContent>
                  <Badge
                    variant={getStatusVariant(
                      health?.services?.storage || "unknown",
                    )}
                  >
                    {health?.services?.storage || "Unknown"}
                  </Badge>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

      {/* Statistics Section */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-foreground mb-4">
          Statistics
        </h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Queries Stats */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Knowledge Service Queries
              </CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-16" />
                  <div className="flex space-x-2">
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-4 w-12" />
                  </div>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">
                    {stats?.queries?.total || 0}
                  </div>
                  <div className="flex space-x-2 text-xs text-muted-foreground mt-2">
                    <span className="text-emerald-600 dark:text-emerald-400">
                      Active: {stats?.queries?.active || 0}
                    </span>
                    <span className="text-blue-600 dark:text-blue-400">
                      Completed: {stats?.queries?.completed || 0}
                    </span>
                    <span className="text-red-600 dark:text-red-400">
                      Failed: {stats?.queries?.failed || 0}
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Specifications Stats */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Assembly Specifications
              </CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-16" />
                  <div className="flex space-x-2">
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-4 w-12" />
                  </div>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">
                    {stats?.specifications?.total || 0}
                  </div>
                  <div className="flex space-x-2 text-xs text-muted-foreground mt-2">
                    <span className="text-emerald-600 dark:text-emerald-400">
                      Active: {stats?.specifications?.active || 0}
                    </span>
                    <span className="text-blue-600 dark:text-blue-400">
                      Completed: {stats?.specifications?.completed || 0}
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Workflows Stats */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Temporal Workflows
              </CardTitle>
              <Workflow className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-16" />
                  <div className="flex space-x-2">
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-4 w-12" />
                  </div>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">
                    {stats?.workflows?.running || 0}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Currently Running
                  </p>
                  <div className="flex space-x-2 text-xs text-muted-foreground mt-2">
                    <span className="text-blue-600 dark:text-blue-400">
                      Completed: {stats?.workflows?.completed || 0}
                    </span>
                    <span className="text-red-600 dark:text-red-400">
                      Failed: {stats?.workflows?.failed || 0}
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-foreground mb-4">
          Quick Actions
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="hover:shadow-md transition-shadow cursor-pointer hover:bg-accent/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Create Query</CardTitle>
              <CardDescription>
                Start a new knowledge service query
              </CardDescription>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-md transition-shadow cursor-pointer hover:bg-accent/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">New Specification</CardTitle>
              <CardDescription>
                Define an assembly specification
              </CardDescription>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-md transition-shadow cursor-pointer hover:bg-accent/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">View Workflows</CardTitle>
              <CardDescription>Monitor active workflows</CardDescription>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-md transition-shadow cursor-pointer hover:bg-accent/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">System Logs</CardTitle>
              <CardDescription>Review system activity</CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>
    </div>
  );
}
