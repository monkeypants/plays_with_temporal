"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";

import {
  ArrowLeft,
  Settings,
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle2,
  Play,
  Hash,
} from "lucide-react";
import { apiClient, getApiErrorMessage } from "@/lib/api-client";
import WorkflowTriggerModal from "@/components/WorkflowTriggerModal";
import JsonSchemaViewer from "@/components/JsonSchemaViewer";

interface AssemblySpecification {
  assembly_specification_id: string;
  name: string;
  applicability: string;
  jsonschema: Record<string, unknown>;
  status: "active" | "inactive" | "draft" | "deprecated";
  knowledge_service_queries: Record<string, string>;
  version: string;
  created_at: string;
  updated_at: string;
}

export default function AssemblySpecificationDetailPage() {
  const { specificationId } = useParams<{ specificationId: string }>();
  const navigate = useNavigate();
  const [showWorkflowModal, setShowWorkflowModal] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const {
    data: specification,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["assembly-specification", specificationId],
    queryFn: async () => {
      if (!specificationId) throw new Error("Specification ID is required");
      const response = await apiClient.get<AssemblySpecification>(
        `/assembly_specifications/${specificationId}`,
      );
      return response.data;
    },
    enabled: !!specificationId,
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

  const handleWorkflowSubmit = async (documentId: string) => {
    if (!specification) return;

    try {
      const response = await apiClient.post("/workflows/extract-assemble", {
        document_id: documentId,
        assembly_specification_id: specification.assembly_specification_id,
      });

      setStatusMessage(
        `Workflow started successfully! Workflow ID: ${response.data.workflow_id}`,
      );
      setShowWorkflowModal(false);
    } catch (error) {
      console.error("Failed to start workflow:", error);
      setStatusMessage(
        `Failed to start workflow: ${getApiErrorMessage(error)}`,
      );
      throw error; // Re-throw to let modal handle the error state
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      case "draft":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      case "inactive":
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
      case "deprecated":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  if (!specificationId) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <div className="ml-2">
            <h4 className="font-medium">Invalid Specification ID</h4>
            <p className="text-sm mt-1">
              No specification ID provided in the URL.
            </p>
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
            onClick={() => navigate("/specifications")}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Specifications
          </Button>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <div className="ml-2">
            <h4 className="font-medium">Failed to load specification</h4>
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
              <Skeleton className="h-48 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!specification) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-4">
          <Button
            variant="ghost"
            onClick={() => navigate("/specifications")}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Specifications
          </Button>
        </div>

        <Alert>
          <AlertCircle className="h-4 w-4" />
          <div className="ml-2">
            <h4 className="font-medium">Specification not found</h4>
            <p className="text-sm mt-1">
              The assembly specification with ID "{specificationId}" was not
              found.
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
          onClick={() => navigate("/specifications")}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Specifications
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Assembly Specification
            </h1>
            <p className="text-muted-foreground">
              View assembly specification configuration and schema
            </p>
          </div>
          <Button
            className="flex items-center gap-2"
            onClick={() => setShowWorkflowModal(true)}
          >
            <Play className="h-4 w-4" />
            Run Assembly
          </Button>
        </div>
      </div>

      {/* Status Message */}
      {statusMessage && (
        <Alert className="mb-6 border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>{statusMessage}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-xl mb-2">
                  {specification.name}
                </CardTitle>
                <CardDescription className="text-base">
                  {specification.applicability}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <Badge className={getStatusColor(specification.status)}>
                  {specification.status.charAt(0).toUpperCase() +
                    specification.status.slice(1)}
                </Badge>
                <Badge variant="outline" className="font-mono">
                  v{specification.version}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>Created</span>
                </div>
                <p className="text-sm font-medium">
                  {formatDate(specification.created_at)}
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>Last Updated</span>
                </div>
                <p className="text-sm font-medium">
                  {formatDate(specification.updated_at)}
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Hash className="h-4 w-4" />
                  <span>Version</span>
                </div>
                <p className="text-sm font-medium">{specification.version}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* JSON Schema with Visual Viewer */}
        <JsonSchemaViewer
          schema={specification.jsonschema}
          knowledgeServiceQueries={specification.knowledge_service_queries}
        />

        {/* Technical Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Technical Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Specification ID
                </dt>
                <dd className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {specification.assembly_specification_id}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Status
                </dt>
                <dd className="mt-1">
                  <Badge className={getStatusColor(specification.status)}>
                    {specification.status.charAt(0).toUpperCase() +
                      specification.status.slice(1)}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Version
                </dt>
                <dd className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {specification.version}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Schema Type
                </dt>
                <dd className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {specification.jsonschema?.type || "object"}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>

      {/* Workflow Trigger Modal */}
      {showWorkflowModal && specification && (
        <WorkflowTriggerModal
          isOpen={true}
          onClose={() => setShowWorkflowModal(false)}
          onSubmit={handleWorkflowSubmit}
          specification={specification}
          isSubmitting={false}
        />
      )}
    </div>
  );
}
