"use client";

import { useQuery } from "@tanstack/react-query";
import { useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Database, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import { apiClient, getApiErrorMessage } from "@/lib/api-client";

interface KnowledgeServiceQuery {
  query_id: string;
  name: string;
  knowledge_service_id: string;
  prompt: string;
  assistant_prompt?: string;
  query_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface QueriesResponse {
  items: KnowledgeServiceQuery[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export default function QueriesPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Check for success message from navigation state
  useEffect(() => {
    if (location.state?.success) {
      // Use setTimeout to avoid synchronous setState in effect
      setTimeout(() => setSuccessMessage(location.state.success), 0);
      // Clear the state to prevent showing the message on refresh
      navigate(location.pathname, { replace: true });
    }
  }, [location.state?.success, location.pathname, navigate]);

  // Auto-dismiss success message after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  const {
    data: queries,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["queries"],
    queryFn: async (): Promise<QueriesResponse> => {
      const response = await apiClient.get(
        "/knowledge_service_queries?size=50",
      );
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const getStatusIcon = () => {
    // For now, all queries are considered active since we don't have status field
    return <CheckCircle2 className="h-4 w-4 text-green-500" />;
  };

  const getStatusBadge = () => {
    // For now, all queries are considered active since we don't have status field
    return <Badge variant="default">Active</Badge>;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleCreateQuery = () => {
    navigate("/queries/create");
  };

  if (isError) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            Knowledge Service Queries
          </h1>
          <p className="text-muted-foreground">
            Manage and monitor your knowledge service queries
          </p>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <div className="ml-2">
            <h4 className="font-medium">Failed to load queries</h4>
            <p className="text-sm mt-1">{getApiErrorMessage(error)}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="mt-2"
            >
              Try Again
            </Button>
          </div>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Knowledge Service Queries
            </h1>
            <p className="text-muted-foreground">
              Manage and monitor your knowledge service queries
            </p>
          </div>
          <Button
            onClick={handleCreateQuery}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Create New Query
          </Button>
        </div>

        {successMessage && (
          <Alert className="mb-6 border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
            <CheckCircle2 className="h-4 w-4" />
            <div className="ml-2">{successMessage}</div>
          </Alert>
        )}
      </div>

      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="h-5 w-16" />
                </div>
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : queries?.items && queries.items.length > 0 ? (
        <>
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Database className="h-4 w-4" />
              <span>{queries.total} queries total</span>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {queries.items.map((query) => (
              <Card
                key={query.query_id}
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => {
                  navigate(`/queries/${query.query_id}`);
                }}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-base line-clamp-2">
                        {query.name}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        Service: {query.knowledge_service_id}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      {getStatusIcon()}
                      {getStatusBadge()}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">
                        Prompt:
                      </p>
                      <p className="text-sm line-clamp-3">{query.prompt}</p>
                    </div>

                    <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
                      <span>Created: {formatDate(query.created_at)}</span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDate(query.updated_at)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {queries.pages > 1 && (
            <div className="mt-8 flex justify-center">
              <p className="text-sm text-muted-foreground">
                Page {queries.page} of {queries.pages}
                {/* TODO: Add pagination controls when needed */}
              </p>
            </div>
          )}
        </>
      ) : (
        <Card className="text-center py-12">
          <CardContent>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 mb-4">
              <Database className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-medium text-foreground mb-2">
              No queries yet
            </h3>
            <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
              Create your first knowledge service query to start extracting
              insights from your documents.
            </p>
            <Button
              onClick={handleCreateQuery}
              className="flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              Create Your First Query
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
