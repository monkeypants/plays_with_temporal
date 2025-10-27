"use client";

import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
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
import { Button } from "@/components/ui/button";

// Reusable error state component for cards
const CardErrorState = () => (
  <div className="text-center py-4">
    <XCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
    <p className="text-sm text-muted-foreground">Failed to load</p>
  </div>
);

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

interface QueryItem {
  status: string;
  // Add other query properties as needed
}

interface SpecificationItem {
  status: string;
  // Add other specification properties as needed
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const {
    data: health,
    isLoading: healthLoading,
    error: healthError,
    isError: healthIsError,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ["system", "health"],
    queryFn: async (): Promise<SystemHealth> => {
      const response = await apiClient.get("/health");
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 3,
    retryDelay: 1000,
  });

  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
    isError: statsIsError,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: async (): Promise<DashboardStats> => {
      // This would be replaced with actual API calls to your FastAPI endpoints
      const [queriesResponse, specsResponse] = await Promise.all([
        apiClient.get("/knowledge_service_queries/?limit=1000"),
        apiClient.get("/assembly_specifications/?limit=1000"),
      ]);

      const queries = queriesResponse.data.items || [];
      const specifications = specsResponse.data.items || [];

      return {
        queries: {
          total: queries.length,
          active: queries.filter((q: QueryItem) => q.status === "active")
            .length,
          completed: queries.filter((q: QueryItem) => q.status === "completed")
            .length,
          failed: queries.filter((q: QueryItem) => q.status === "failed")
            .length,
        },
        specifications: {
          total: specifications.length,
          active: specifications.filter(
            (s: SpecificationItem) => s.status === "active",
          ).length,
          completed: specifications.filter(
            (s: SpecificationItem) => s.status === "completed",
          ).length,
        },
        workflows: {
          running: 5, // Mock data - would come from Temporal API
          completed: 127,
          failed: 3,
        },
      };
    },
    refetchInterval: 60000, // Refresh every minute
    retry: 2,
    retryDelay: 2000,
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
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Dashboard
            </h1>
            <p className="text-muted-foreground">
              Overview of your workflow system
            </p>
          </div>
          <div className="flex items-center gap-2">
            {healthIsError ? (
              <Badge variant="destructive" className="flex items-center gap-1">
                <XCircle className="h-3 w-3" />
                API Disconnected
              </Badge>
            ) : healthLoading ? (
              <Badge variant="secondary" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Connecting...
              </Badge>
            ) : (
              <Badge variant="default" className="flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                Connected
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* System Health Section */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-foreground mb-4">
          System Health
        </h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {healthIsError ? (
            <div className="col-span-full">
              <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
                <CardHeader>
                  <CardTitle className="text-red-800 dark:text-red-200 flex items-center gap-2">
                    <XCircle className="h-5 w-5" />
                    Unable to Connect to API
                  </CardTitle>
                  <CardDescription className="text-red-600 dark:text-red-400">
                    {healthError?.message || "Failed to fetch system health"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetchHealth()}
                    disabled={healthLoading}
                    className="text-red-700 border-red-300 hover:bg-red-100 dark:text-red-300 dark:border-red-700 dark:hover:bg-red-900"
                  >
                    {healthLoading ? "Retrying..." : "Retry Connection"}
                  </Button>
                </CardContent>
              </Card>
            </div>
          ) : healthLoading ? (
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
        {statsIsError ? (
          <Card className="border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950 mb-6">
            <CardHeader>
              <CardTitle className="text-yellow-800 dark:text-yellow-200 flex items-center gap-2">
                <AlertCircle className="h-5 w-5" />
                Unable to Load Statistics
              </CardTitle>
              <CardDescription className="text-yellow-600 dark:text-yellow-400">
                {statsError?.message || "Failed to fetch dashboard statistics"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchStats()}
                disabled={statsLoading}
                className="text-yellow-700 border-yellow-300 hover:bg-yellow-100 dark:text-yellow-300 dark:border-yellow-700 dark:hover:bg-yellow-900"
              >
                {statsLoading ? "Retrying..." : "Retry Loading"}
              </Button>
            </CardContent>
          </Card>
        ) : null}
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
              ) : statsIsError ? (
                <CardErrorState />
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
              ) : statsIsError ? (
                <CardErrorState />
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
              ) : statsIsError ? (
                <CardErrorState />
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
          <Card
            className="hover:shadow-md transition-shadow cursor-pointer hover:bg-accent/50"
            onClick={() => navigate("/queries/create")}
          >
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
