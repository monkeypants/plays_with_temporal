"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useState } from "react";
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
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { apiClient, getApiErrorMessage } from "@/lib/api-client";
import JsonSchemaEditor from "@/components/JsonSchemaEditor";

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
  onSuccess?: (spec: unknown) => void;
  onCancel?: () => void;
}

// Interface will be used when implementing query creation modal
// interface KnowledgeServiceQuery {
//   query_id: string;
//   name: string;
//   prompt: string;
//   knowledge_service_id: string;
//   created_at: string;
//   updated_at: string;
// }

// Interface will be used when implementing query creation modal
// interface KnowledgeServiceQueriesResponse {
//   items: KnowledgeServiceQuery[];
//   total: number;
//   page: number;
//   size: number;
//   pages: number;
// }

// Example JSON schemas for different assembly types

export default function AssemblySpecificationForm({
  onSuccess,
  onCancel,
}: AssemblySpecificationFormProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Separate state for knowledge service queries to avoid form interference
  const [knowledgeServiceQueries, setKnowledgeServiceQueries] = useState<
    Record<string, string>
  >({});

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
  // TODO: This query will be used when implementing query creation modal
  // const { data: _queriesData } = useQuery({
  //   queryKey: ["knowledge-service-queries"],
  //   queryFn: async (): Promise<KnowledgeServiceQueriesResponse> => {
  //     const response = await apiClient.get(
  //       "/knowledge_service_queries/?size=50",
  //     );
  //     return response.data;
  //   },
  // });

  const createSpecMutation = useMutation({
    mutationFn: async (data: unknown) => {
      const response = await apiClient.post("/assembly_specifications/", data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["assembly-specifications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });

      if (onSuccess) {
        onSuccess(data);
      } else {
        navigate("/specifications", {
          state: {
            message: `Assembly specification "${data.name}" created successfully!`,
          },
        });
      }
    },
  });

  const onSubmit = (data: AssemblySpecFormValues) => {
    // Prepare data for submission
    let parsedJsonSchema = {};

    // Parse JSON schema
    try {
      parsedJsonSchema = JSON.parse(data.jsonschema);
    } catch {
      form.setError("jsonschema", {
        message: "Invalid JSON format in schema",
      });
      return;
    }
    // Use the separate state instead of parsing from form

    const submitData = {
      name: data.name.trim(),
      applicability: data.applicability.trim(),
      jsonschema: parsedJsonSchema,
      knowledge_service_queries: knowledgeServiceQueries,
      version: data.version.trim(),
    };

    createSpecMutation.mutate(submitData);
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      navigate(-1);
    }
  };

  return (
    <div className="space-y-8">
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
              <JsonSchemaEditor
                value={form.getValues("jsonschema") || "{}"}
                onChange={(value) => form.setValue("jsonschema", value)}
                label="Data to assemble"
                description="JSON Schema defining the structure of data to be extracted for this assembly"
                error={form.formState.errors.jsonschema?.message}
                knowledgeServiceQueries={knowledgeServiceQueries}
                onFieldSelect={(_jsonPointer) => {
                  // Field navigation is now handled by DOM simulation in JsonSchemaEditor
                }}
                onUpdateQuery={(jsonPointer, queryId) => {
                  const updatedQueries = { ...knowledgeServiceQueries };
                  if (queryId === null) {
                    delete updatedQueries[jsonPointer];
                  } else {
                    updatedQueries[jsonPointer] = queryId;
                  }
                  setKnowledgeServiceQueries(updatedQueries);
                }}
              />

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
                  <FieldError>
                    {form.formState.errors.version.message}
                  </FieldError>
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
    </div>
  );
}
