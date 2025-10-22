"use client";

import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldSet,
  FieldGroup,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { apiClient, getApiErrorMessage } from "@/lib/api-client";

// Form validation schema
const assemblySpecFormSchema = z.object({
  name: z
    .string()
    .min(1, "Name is required")
    .max(200, "Name must be less than 200 characters"),
  applicability: z
    .string()
    .min(1, "Applicability is required")
    .max(1000, "Applicability must be less than 1000 characters"),
  jsonschema: z
    .string()
    .min(1, "JSON Schema is required")
    .refine((val) => {
      try {
        JSON.parse(val);
        return true;
      } catch {
        return false;
      }
    }, "Must be valid JSON"),
  knowledge_service_queries: z
    .string()
    .optional()
    .refine((val) => {
      if (!val || val.trim() === "") return true;
      try {
        JSON.parse(val);
        return true;
      } catch {
        return false;
      }
    }, "Must be valid JSON"),
  version: z
    .string()
    .min(1, "Version is required")
    .max(50, "Version must be less than 50 characters"),
});

type AssemblySpecFormValues = z.infer<typeof assemblySpecFormSchema>;

interface AssemblySpecificationFormProps {
  onSuccess?: (spec: any) => void;
  onCancel?: () => void;
}

interface KnowledgeServiceQuery {
  query_id: string;
  name: string;
  prompt: string;
  knowledge_service_id: string;
  created_at: string;
  updated_at: string;
}

interface KnowledgeServiceQueriesResponse {
  items: KnowledgeServiceQuery[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Example JSON schemas for different assembly types
const EXAMPLE_SCHEMAS = [
  {
    name: "Meeting Minutes",
    schema: {
      $schema: "http://json-schema.org/draft-07/schema#",
      title: "Meeting Minutes",
      type: "object",
      properties: {
        meeting_info: {
          type: "object",
          properties: {
            title: { type: "string" },
            date: { type: "string", format: "date" },
            attendees: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  name: { type: "string" },
                  role: { type: "string" },
                },
              },
            },
          },
        },
        agenda_items: {
          type: "array",
          items: {
            type: "object",
            properties: {
              topic: { type: "string" },
              decisions: {
                type: "array",
                items: { type: "string" },
              },
            },
          },
        },
      },
    },
  },
  {
    name: "Document Summary",
    schema: {
      $schema: "http://json-schema.org/draft-07/schema#",
      title: "Document Summary",
      type: "object",
      properties: {
        title: { type: "string" },
        summary: { type: "string" },
        key_points: {
          type: "array",
          items: { type: "string" },
        },
        metadata: {
          type: "object",
          properties: {
            author: { type: "string" },
            date_created: { type: "string", format: "date" },
          },
        },
      },
    },
  },
  {
    name: "Project Report",
    schema: {
      $schema: "http://json-schema.org/draft-07/schema#",
      title: "Project Report",
      type: "object",
      properties: {
        project_info: {
          type: "object",
          properties: {
            name: { type: "string" },
            status: { type: "string", enum: ["active", "completed", "paused"] },
            start_date: { type: "string", format: "date" },
            end_date: { type: "string", format: "date" },
          },
        },
        deliverables: {
          type: "array",
          items: {
            type: "object",
            properties: {
              name: { type: "string" },
              status: { type: "string" },
              due_date: { type: "string", format: "date" },
            },
          },
        },
      },
    },
  },
];

export default function AssemblySpecificationForm({
  onSuccess,
  onCancel,
}: AssemblySpecificationFormProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const form = useForm<AssemblySpecFormValues>({
    resolver: zodResolver(assemblySpecFormSchema),
    defaultValues: {
      name: "",
      applicability: "",
      jsonschema: "{}",
      knowledge_service_queries: "{}",
      version: "0.1.0",
    },
  });

  // Fetch available knowledge service queries
  const {
    data: queriesData,
    isLoading: isLoadingQueries,
    isError: isQueriesError,
  } = useQuery({
    queryKey: ["knowledge-service-queries"],
    queryFn: async (): Promise<KnowledgeServiceQueriesResponse> => {
      const response = await apiClient.get(
        "/knowledge_service_queries/?size=50",
      );
      return response.data;
    },
  });

  const availableQueries = queriesData?.items || [];

  const createSpecMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.post("/assembly_specifications/", data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["assembly-specifications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });

      if (onSuccess) {
        onSuccess(data);
      } else {
        navigate("/specifications");
      }
    },
  });

  const onSubmit = (data: AssemblySpecFormValues) => {
    // Prepare data for submission
    let parsedJsonSchema = {};
    let parsedKnowledgeServiceQueries = {};

    // Parse JSON schema
    try {
      parsedJsonSchema = JSON.parse(data.jsonschema);
    } catch (error) {
      form.setError("jsonschema", {
        message: "Invalid JSON format in schema",
      });
      return;
    }

    // Parse knowledge service queries if provided
    if (data.knowledge_service_queries?.trim()) {
      try {
        parsedKnowledgeServiceQueries = JSON.parse(
          data.knowledge_service_queries,
        );
      } catch (error) {
        form.setError("knowledge_service_queries", {
          message: "Invalid JSON format in knowledge service queries",
        });
        return;
      }
    }

    const submitData = {
      name: data.name.trim(),
      applicability: data.applicability.trim(),
      jsonschema: parsedJsonSchema,
      knowledge_service_queries: parsedKnowledgeServiceQueries,
      version: data.version.trim(),
    };

    createSpecMutation.mutate(submitData);
  };

  const handleExampleSchema = (exampleSchema: any) => {
    form.setValue("jsonschema", JSON.stringify(exampleSchema, null, 2));
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      navigate(-1);
    }
  };

  return (
    <Card className="max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>Create Assembly Specification</CardTitle>
        <CardDescription>
          Define a new assembly specification that describes how to structure
          extracted data into a specific document type
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Error Alert */}
          {createSpecMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <div className="ml-2">
                {getApiErrorMessage(createSpecMutation.error)}
              </div>
            </Alert>
          )}

          {/* Success Alert */}
          {createSpecMutation.isSuccess && (
            <Alert className="border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
              <CheckCircle2 className="h-4 w-4" />
              <div className="ml-2">
                Assembly specification created successfully! Redirecting...
              </div>
            </Alert>
          )}

          <FieldSet>
            {/* Assembly Name */}
            <Field>
              <Label htmlFor="name">Assembly Name</Label>
              <Input
                id="name"
                placeholder="e.g., Meeting Minutes"
                {...form.register("name")}
                className={form.formState.errors.name ? "border-red-500" : ""}
              />
              <FieldDescription>
                A human-readable name for this assembly type
              </FieldDescription>
              {form.formState.errors.name && (
                <FieldError>{form.formState.errors.name.message}</FieldError>
              )}
            </Field>

            {/* Applicability */}
            <Field>
              <Label htmlFor="applicability">Applicability</Label>
              <Textarea
                id="applicability"
                placeholder="Describe what type of information this assembly applies to..."
                className={`min-h-[100px] ${
                  form.formState.errors.applicability ? "border-red-500" : ""
                }`}
                {...form.register("applicability")}
              />
              <FieldDescription>
                Description of what type of information this assembly applies
                to, used for document-assembly matching
              </FieldDescription>
              {form.formState.errors.applicability && (
                <FieldError>
                  {form.formState.errors.applicability.message}
                </FieldError>
              )}
            </Field>

            {/* JSON Schema */}
            <Field>
              <Label htmlFor="jsonschema">JSON Schema</Label>
              <Textarea
                id="jsonschema"
                placeholder="Enter the JSON schema that defines the data structure..."
                className={`min-h-[200px] font-mono text-sm ${
                  form.formState.errors.jsonschema ? "border-red-500" : ""
                }`}
                {...form.register("jsonschema")}
              />
              <FieldDescription>
                JSON Schema defining the structure of data to be extracted for
                this assembly
              </FieldDescription>
              {form.formState.errors.jsonschema && (
                <FieldError>
                  {form.formState.errors.jsonschema.message}
                </FieldError>
              )}
            </Field>

            {/* Example Schemas */}
            <Field>
              <Label>Example Schemas</Label>
              <FieldGroup>
                <div className="grid gap-2 md:grid-cols-3">
                  {EXAMPLE_SCHEMAS.map((example, index) => (
                    <Button
                      key={index}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-auto p-3 text-left justify-start min-h-[60px]"
                      onClick={() => handleExampleSchema(example.schema)}
                    >
                      <div className="w-full">
                        <div className="font-medium text-xs mb-1">
                          {example.name}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Click to load this schema template
                        </div>
                      </div>
                    </Button>
                  ))}
                </div>
              </FieldGroup>
              <FieldDescription>
                Click any example to use it as a starting point for your schema
              </FieldDescription>
            </Field>

            {/* Knowledge Service Queries */}
            <Field>
              <Label htmlFor="knowledge_service_queries">
                Knowledge Service Queries (Optional)
              </Label>
              <Textarea
                id="knowledge_service_queries"
                placeholder='{"\/properties\/meeting_info": "query-id-1", "\/properties\/agenda_items": "query-id-2"}'
                className={`min-h-[100px] font-mono text-sm ${
                  form.formState.errors.knowledge_service_queries
                    ? "border-red-500"
                    : ""
                }`}
                {...form.register("knowledge_service_queries")}
              />
              <FieldDescription>
                JSON mapping from JSON Pointer paths to Knowledge Service Query
                IDs. Leave empty if not using queries yet.
              </FieldDescription>
              {form.formState.errors.knowledge_service_queries && (
                <FieldError>
                  {form.formState.errors.knowledge_service_queries.message}
                </FieldError>
              )}
            </Field>

            {/* Available Queries Reference */}
            {availableQueries.length > 0 && (
              <Field>
                <Label>Available Knowledge Service Queries</Label>
                <FieldGroup>
                  <div className="grid gap-2 md:grid-cols-2 max-h-40 overflow-y-auto">
                    {availableQueries.map((query) => (
                      <div
                        key={query.query_id}
                        className="p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs"
                      >
                        <div className="font-medium">{query.name}</div>
                        <div className="text-muted-foreground font-mono">
                          {query.query_id}
                        </div>
                      </div>
                    ))}
                  </div>
                </FieldGroup>
                <FieldDescription>
                  Reference: Available query IDs you can use in the mapping
                  above
                </FieldDescription>
              </Field>
            )}

            {/* Version */}
            <Field>
              <Label htmlFor="version">Version</Label>
              <Input
                id="version"
                placeholder="e.g., 0.1.0"
                {...form.register("version")}
                className={
                  form.formState.errors.version ? "border-red-500" : ""
                }
              />
              <FieldDescription>
                Version identifier for this assembly definition
              </FieldDescription>
              {form.formState.errors.version && (
                <FieldError>{form.formState.errors.version.message}</FieldError>
              )}
            </Field>
          </FieldSet>

          {/* Action Buttons */}
          <div className="flex gap-4 pt-4">
            <Button
              type="submit"
              disabled={createSpecMutation.isPending}
              className="flex-1 md:flex-initial"
            >
              {createSpecMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Assembly Specification"
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={createSpecMutation.isPending}
            >
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
