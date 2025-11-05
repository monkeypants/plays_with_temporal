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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Plus,
  FileText,
  Settings,
  CheckCircle2,
  Clock,
  AlertCircle,
  XCircle,
  Play,
  Loader2,
} from "lucide-react";
import { apiClient, getApiErrorMessage } from "@/lib/api-client";
import WorkflowTriggerModal from "@/components/WorkflowTriggerModal";

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

interface SpecificationsResponse {
  items: AssemblySpecification[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case "active":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "draft":
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case "inactive":
      return <XCircle className="h-4 w-4 text-gray-500" />;
    case "deprecated":
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Settings className="h-4 w-4 text-blue-500" />;
  }
};

const getStatusBadge = (status: string) => {
  const statusConfig = {
    active: { variant: "default" as const, label: "Active" },
    draft: { variant: "secondary" as const, label: "Draft" },
    inactive: { variant: "outline" as const, label: "Inactive" },
    deprecated: { variant: "destructive" as const, label: "Deprecated" },
  };

  const config = statusConfig[status as keyof typeof statusConfig] || {
    variant: "outline" as const,
    label: status,
  };

  return (
    <Badge variant={config.variant} className="capitalize">
      {config.label}
    </Badge>
  );
};

const LoadingSkeleton = () => (
  <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
    {Array.from({ length: 6 }).map((_, i) => (
      <Card key={i}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-16" />
          </div>
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
          </div>
          <div className="flex items-center justify-between mt-4">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

export default function SpecificationsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [runningWorkflows, setRunningWorkflows] = useState<Set<string>>(
    new Set(),
  );
  const [modalSpec, setModalSpec] = useState<AssemblySpecification | null>(
    null,
  );

  // Check for success message from navigation state
  useEffect(() => {
    if (location.state?.message) {
      // Use setTimeout to avoid synchronous setState in effect
      setTimeout(() => setStatusMessage(location.state.message), 0);
      // Clear the navigation state to prevent showing the message on refresh
      navigate(location.pathname, { replace: true });
    }
  }, [location.state?.message, location.pathname, navigate]);

  // Auto-dismiss success message after 5 seconds
  useEffect(() => {
    if (statusMessage) {
      const timer = setTimeout(() => setStatusMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [statusMessage]);

  const {
    data: specificationsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["assembly-specifications"],
    queryFn: async (): Promise<SpecificationsResponse> => {
      const response = await apiClient.get("/assembly_specifications/?size=50");
      return response.data;
    },
    refetchOnWindowFocus: false,
  });

  const specifications = specificationsData?.items || [];

  const handleCreateNew = () => {
    navigate("/specifications/create");
  };

  const handleRunAssembly = (spec: AssemblySpecification) => {
    setModalSpec(spec);
  };

  const handleModalSubmit = async (documentId: string) => {
    if (!modalSpec) return;

    try {
      setRunningWorkflows(
        (prev) => new Set([...prev, modalSpec.assembly_specification_id]),
      );

      const response = await apiClient.post("/workflows/extract-assemble", {
        document_id: documentId,
        assembly_specification_id: modalSpec.assembly_specification_id,
      });

      setStatusMessage(
        `Workflow started successfully! Workflow ID: ${response.data.workflow_id}`,
      );

      // Navigate to a workflow monitoring page (we'll create this later)
      // navigate(`/workflows/${response.data.workflow_id}`);
    } catch (error) {
      console.error("Failed to start workflow:", error);
      setStatusMessage(
        `Failed to start workflow: ${getApiErrorMessage(error)}`,
      );
      throw error; // Re-throw to let modal handle the error state
    } finally {
      setRunningWorkflows((prev) => {
        const newSet = new Set(prev);
        newSet.delete(modalSpec.assembly_specification_id);
        return newSet;
      });
    }
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Assembly Specifications
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Define and manage assembly specifications for your workflows
            </p>
          </div>
          <Button onClick={handleCreateNew} className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Create New Specification
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

      {/* Error State */}
      {isError && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <div className="font-medium">Failed to load specifications</div>
            <div className="text-sm mt-1">
              {getApiErrorMessage(error)}
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                className="ml-2"
              >
                Try Again
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {isLoading && <LoadingSkeleton />}

      {/* Empty State */}
      {!isLoading && !isError && specifications.length === 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900">
              <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
              No Assembly Specifications
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Get started by creating your first assembly specification.
            </p>
            <div className="mt-6">
              <Button onClick={handleCreateNew}>
                <Plus className="h-4 w-4 mr-2" />
                Create New Specification
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Specifications Grid */}
      {!isLoading && !isError && specifications.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {specifications.map((spec) => (
            <Card
              key={spec.assembly_specification_id}
              className="hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => {
                navigate(`/specifications/${spec.assembly_specification_id}`);
              }}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{spec.name}</CardTitle>
                  {getStatusBadge(spec.status)}
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  {getStatusIcon(spec.status)}
                  <span>Version {spec.version}</span>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-sm mb-4 line-clamp-3">
                  {spec.applicability}
                </CardDescription>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">Schema Fields:</span>
                    <span className="font-medium">
                      {Object.keys(spec.jsonschema?.properties || {}).length}{" "}
                      fields
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">Query Mappings:</span>
                    <span className="font-medium">
                      {Object.keys(spec.knowledge_service_queries || {}).length}{" "}
                      mappings
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-xs text-gray-500">
                    Created {new Date(spec.created_at).toLocaleDateString()}
                  </div>
                  <div className="text-xs font-mono text-gray-400">
                    {spec.assembly_specification_id.split("-")[0]}...
                  </div>
                </div>

                {/* Run Assembly Button */}
                <div className="mt-4">
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRunAssembly(spec);
                    }}
                    disabled={runningWorkflows.has(
                      spec.assembly_specification_id,
                    )}
                    className="w-full"
                    variant={spec.status === "active" ? "default" : "outline"}
                  >
                    {runningWorkflows.has(spec.assembly_specification_id) ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Starting Workflow...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Run Assembly
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Stats Footer */}
      {!isLoading && !isError && specifications.length > 0 && (
        <div className="mt-8 bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
            <div>
              Showing {specifications.length} of{" "}
              {specificationsData?.total || 0} specifications
            </div>
            <div className="flex items-center gap-4">
              <span>
                Active:{" "}
                {specifications.filter((s) => s.status === "active").length}
              </span>
              <span>
                Draft:{" "}
                {specifications.filter((s) => s.status === "draft").length}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Workflow Trigger Modal */}
      {modalSpec && (
        <WorkflowTriggerModal
          isOpen={true}
          onClose={() => setModalSpec(null)}
          onSubmit={handleModalSubmit}
          specification={modalSpec}
          isSubmitting={runningWorkflows.has(
            modalSpec.assembly_specification_id,
          )}
        />
      )}
    </div>
  );
}
