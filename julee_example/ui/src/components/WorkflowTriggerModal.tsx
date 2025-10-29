import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import {
  FileText,
  Calendar,
  Hash,
  AlertCircle,
  Play,
  Loader2,
} from "lucide-react";
import { apiClient, getApiErrorMessage } from "@/lib/api-client";

interface Document {
  document_id: string;
  original_filename: string;
  content_type: string;
  status: string;
  created_at: string;
}

interface DocumentsResponse {
  items: Document[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface AssemblySpecification {
  assembly_specification_id: string;
  name: string;
  applicability: string;
  status: "active" | "inactive" | "draft" | "deprecated";
  version: string;
}

interface WorkflowTriggerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (documentId: string) => Promise<void>;
  specification: AssemblySpecification;
  isSubmitting?: boolean;
}

export default function WorkflowTriggerModal({
  isOpen,
  onClose,
  onSubmit,
  specification,
  isSubmitting = false,
}: WorkflowTriggerModalProps) {
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>("");

  const {
    data: documentsData,
    isLoading: isLoadingDocuments,
    error: documentsError,
  } = useQuery({
    queryKey: [
      "workflow-trigger-documents",
      specification.assembly_specification_id,
    ],
    queryFn: async (): Promise<DocumentsResponse> => {
      const response = await apiClient.get("/documents/?size=50");
      return response.data;
    },
    refetchOnWindowFocus: false,
    enabled: isOpen, // Only fetch when modal is open
  });

  const documents = documentsData?.items || [];

  const handleSubmit = async () => {
    if (!selectedDocumentId) return;

    try {
      await onSubmit(selectedDocumentId);
      // Reset form on successful submission
      setSelectedDocumentId("");
      onClose();
    } catch (error) {
      // Error handling is done in the parent component
      console.error("Error starting workflow:", error);
    }
  };

  const handleClose = () => {
    setSelectedDocumentId("");
    onClose();
  };

  const selectedDocument = documents.find(
    (doc) => doc.document_id === selectedDocumentId,
  );

  const isFormValid = selectedDocumentId && !isSubmitting;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Run Assembly Workflow</DialogTitle>
          <DialogDescription>
            Select a document to process with the "{specification.name}"
            assembly specification.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Assembly Specification Info */}
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Hash className="h-4 w-4 text-blue-500" />
              <span className="font-medium">Assembly Specification</span>
            </div>
            <div className="text-sm space-y-1">
              <div className="font-medium">{specification.name}</div>
              <div className="text-gray-600 dark:text-gray-400">
                {specification.applicability}
              </div>
              <div className="text-xs text-gray-500">
                Version {specification.version} • Status: {specification.status}
              </div>
            </div>
          </div>

          {/* Document Selection */}
          <div className="space-y-2">
            <Label htmlFor="document-select">Select Document</Label>
            {isLoadingDocuments ? (
              <Skeleton className="h-10 w-full" />
            ) : documentsError ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Failed to load documents: {getApiErrorMessage(documentsError)}
                </AlertDescription>
              </Alert>
            ) : documents.length === 0 ? (
              <Alert>
                <FileText className="h-4 w-4" />
                <AlertDescription>
                  No documents available. Please upload documents first.
                </AlertDescription>
              </Alert>
            ) : (
              <Select
                value={selectedDocumentId}
                onValueChange={setSelectedDocumentId}
              >
                <SelectTrigger id="document-select">
                  <SelectValue placeholder="Choose a document..." />
                </SelectTrigger>
                <SelectContent>
                  {documents.map((document) => (
                    <SelectItem
                      key={document.document_id}
                      value={document.document_id}
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-blue-500" />
                        <div className="flex flex-col">
                          <span className="font-medium">
                            {document.original_filename}
                          </span>
                          <span className="text-xs text-gray-500">
                            {document.content_type}
                          </span>
                        </div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Selected Document Preview */}
          {selectedDocument && (
            <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="h-4 w-4 text-blue-500" />
                <span className="font-medium">Selected Document</span>
              </div>
              <div className="text-sm space-y-1">
                <div className="font-medium">
                  {selectedDocument.original_filename}
                </div>
                <div className="text-gray-600 dark:text-gray-400">
                  {selectedDocument.content_type}
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Created{" "}
                    {new Date(selectedDocument.created_at).toLocaleDateString()}
                  </div>
                  <div>Status: {selectedDocument.status}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isFormValid}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Starting Workflow...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Start Assembly
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
