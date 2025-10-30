"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
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
import {
  ArrowLeft,
  Database,
  Clock,
  AlertCircle,
  Calendar,
  Settings,
  FileText,
} from "lucide-react";
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

export default function QueryDetailPage() {
  const { queryId } = useParams<{ queryId: string }>();
  const navigate = useNavigate();

  const {
    data: query,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["query", queryId],
    queryFn: async () => {
      if (!queryId) throw new Error("Query ID is required");
      const response = await apiClient.get<KnowledgeServiceQuery>(
        `/knowledge_service_queries/${queryId}`,
      );
      return response.data;
    },
    enabled: !!queryId,
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatMetadata = (metadata: Record<string, unknown>) => {
    if (!metadata || Object.keys(metadata).length === 0) {
      return "None";
    }
    return JSON.stringify(metadata, null, 2);
  };

  if (!queryId) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <div className="ml-2">
            <h4 className="font-medium">Invalid Query ID</h4>
            <p className="text-sm mt-1">No query ID provided in the URL.</p>
          </div>
        </Alert>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-4">
          <Button
            variant="ghost"
            onClick={() => navigate("/queries")}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Queries
          </Button>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <div className="ml-2">
            <h4 className="font-medium">Failed to load query</h4>
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

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-4">
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-8 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-1/3" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-32 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!query) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-4">
          <Button
            variant="ghost"
            onClick={() => navigate("/queries")}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Queries
          </Button>
        </div>

        <Alert>
          <AlertCircle className="h-4 w-4" />
          <div className="ml-2">
            <h4 className="font-medium">Query not found</h4>
            <p className="text-sm mt-1">
              The query with ID "{queryId}" was not found.
            </p>
          </div>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header with back button */}
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => navigate("/queries")}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Queries
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Query Details
            </h1>
            <p className="text-muted-foreground">
              View and manage knowledge service query configuration
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-xl mb-2">{query.name}</CardTitle>
                <CardDescription className="flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Knowledge Service: {query.knowledge_service_id}
                </CardDescription>
              </div>
              <Badge variant="secondary" className="flex items-center gap-1">
                <Settings className="h-3 w-3" />
                Active
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>Created</span>
                </div>
                <p className="text-sm font-medium">
                  {formatDate(query.created_at)}
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>Last Updated</span>
                </div>
                <p className="text-sm font-medium">
                  {formatDate(query.updated_at)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Query Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Query Configuration
            </CardTitle>
            <CardDescription>
              The prompt and settings used for this knowledge service query
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">
                Main Prompt
              </h4>
              <div className="bg-muted p-4 rounded-md">
                <pre className="text-sm whitespace-pre-wrap font-mono">
                  {query.prompt}
                </pre>
              </div>
            </div>

            {query.assistant_prompt && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">
                  Assistant Prompt
                </h4>
                <div className="bg-muted p-4 rounded-md">
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {query.assistant_prompt}
                  </pre>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Metadata */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Query Metadata
            </CardTitle>
            <CardDescription>
              Additional configuration and parameters for this query
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-muted p-4 rounded-md">
              <pre className="text-sm font-mono">
                {formatMetadata(query.query_metadata)}
              </pre>
            </div>
          </CardContent>
        </Card>

        {/* Technical Details */}
        <Card>
          <CardHeader>
            <CardTitle>Technical Details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Query ID
                </dt>
                <dd className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {query.query_id}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Knowledge Service ID
                </dt>
                <dd className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {query.knowledge_service_id}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
