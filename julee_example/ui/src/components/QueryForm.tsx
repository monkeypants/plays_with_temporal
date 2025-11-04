"use client";

import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useForm, useWatch } from "react-hook-form";
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
const queryFormSchema = z.object({
  name: z
    .string()
    .min(1, "Name is required")
    .max(200, "Name must be less than 200 characters"),
  knowledge_service_id: z
    .string()
    .min(1, "Knowledge service is required")
    .max(100, "Knowledge service ID must be less than 100 characters"),
  prompt: z
    .string()
    .min(1, "Prompt is required")
    .max(5000, "Prompt must be less than 5000 characters"),
  assistant_prompt: z
    .string()
    .max(2000, "Assistant prompt must be less than 2000 characters")
    .optional(),
  query_metadata: z.string().optional(),
});

type QueryFormValues = z.infer<typeof queryFormSchema>;

interface QueryFormProps {
  onSuccess?: (query: unknown) => void;
  onCancel?: () => void;
}

interface KnowledgeServiceConfig {
  knowledge_service_id: string;
  name: string;
  description: string;
  service_api: string;
  created_at: string;
  updated_at: string;
}

interface KnowledgeServiceConfigsResponse {
  items: KnowledgeServiceConfig[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Example prompts for different use cases
const EXAMPLE_PROMPTS = [
  {
    name: "Meeting Summary",
    prompt:
      "Extract the key points, decisions made, and action items from this meeting transcript. Format the response as a structured summary with clear sections for agenda items, decisions, and next steps.",
  },
  {
    name: "Document Analysis",
    prompt:
      "Analyze this document and extract the main topics, key findings, and any recommendations or conclusions. Provide a concise summary highlighting the most important information.",
  },
  {
    name: "Action Items Extraction",
    prompt:
      "Identify all action items, tasks, and to-do items mentioned in this text. For each item, extract who is responsible (if mentioned) and any deadlines or due dates.",
  },
  {
    name: "Risk Assessment",
    prompt:
      "Analyze this content for potential risks, concerns, or issues. Categorize risks by severity and provide a brief explanation of each identified risk.",
  },
];

export default function QueryForm({ onSuccess, onCancel }: QueryFormProps) {
  const navigate = useNavigate(); // Used as fallback when props are not provided
  const queryClient = useQueryClient();

  const form = useForm<QueryFormValues>({
    resolver: zodResolver(queryFormSchema),
    defaultValues: {
      name: "",
      knowledge_service_id: "",
      prompt: "",
      assistant_prompt: "",
      query_metadata: "{}",
    },
  });

  // Watch for knowledge_service_id changes
  const selectedServiceId = useWatch({
    control: form.control,
    name: "knowledge_service_id",
  });

  // Fetch knowledge service configurations
  const {
    data: knowledgeServicesData,
    isLoading: isLoadingServices,
    isError: isServicesError,
  } = useQuery({
    queryKey: ["knowledge-service-configs"],
    queryFn: async (): Promise<KnowledgeServiceConfigsResponse> => {
      const response = await apiClient.get(
        "/knowledge_service_configs/?size=50",
      );
      return response.data;
    },
  });

  const knowledgeServices = knowledgeServicesData?.items || [];

  const createQueryMutation = useMutation({
    mutationFn: async (data: unknown) => {
      const response = await apiClient.post(
        "/knowledge_service_queries/",
        data,
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate queries to refresh the list
      queryClient.invalidateQueries({ queryKey: ["queries"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });

      if (onSuccess) {
        onSuccess(data);
      } else {
        navigate("/queries");
      }
    },
  });

  const onSubmit = (data: QueryFormValues) => {
    // Prepare data for submission
    let parsedMetadata = {};
    if (data.query_metadata?.trim()) {
      try {
        parsedMetadata = JSON.parse(data.query_metadata);
      } catch {
        form.setError("query_metadata", {
          message: "Invalid JSON format in metadata",
        });
        return;
      }
    }

    const submitData = {
      name: data.name.trim(),
      knowledge_service_id: data.knowledge_service_id,
      prompt: data.prompt.trim(),
      assistant_prompt: data.assistant_prompt?.trim() || undefined,
      query_metadata: parsedMetadata,
    };

    createQueryMutation.mutate(submitData);
  };

  const handleServiceSelect = (serviceId: string) => {
    form.setValue("knowledge_service_id", serviceId);
  };

  const handleExamplePrompt = (examplePrompt: string) => {
    form.setValue("prompt", examplePrompt);
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
        <CardTitle>Create Knowledge Service Query</CardTitle>
        <CardDescription>
          Define a new query to extract specific information using AI services
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Error Alert */}
          {createQueryMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <div className="ml-2">
                {getApiErrorMessage(createQueryMutation.error)}
              </div>
            </Alert>
          )}

          {/* Success Alert */}
          {createQueryMutation.isSuccess && (
            <Alert className="border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
              <CheckCircle2 className="h-4 w-4" />
              <div className="ml-2">
                Query created successfully! Redirecting...
              </div>
            </Alert>
          )}

          <FieldSet>
            {/* Query Name */}
            <Field>
              <Label htmlFor="name">Query Name</Label>
              <Input
                id="name"
                placeholder="e.g., Extract Meeting Summary"
                {...form.register("name")}
                className={form.formState.errors.name ? "border-red-500" : ""}
              />
              <FieldDescription>
                A descriptive name for this query configuration
              </FieldDescription>
              {form.formState.errors.name && (
                <FieldError>{form.formState.errors.name.message}</FieldError>
              )}
            </Field>

            {/* Knowledge Service Selection */}
            <Field>
              <Label>Knowledge Service</Label>
              <FieldGroup>
                {isLoadingServices ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2">Loading services...</span>
                  </div>
                ) : isServicesError ? (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <div className="ml-2">
                      Failed to load knowledge services. Please try again.
                    </div>
                  </Alert>
                ) : knowledgeServices.length === 0 ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <div className="ml-2">
                      No knowledge services available. Contact your
                      administrator.
                    </div>
                  </Alert>
                ) : (
                  <div className="grid gap-3 md:grid-cols-3">
                    {knowledgeServices.map((service) => (
                      <Card
                        key={service.knowledge_service_id}
                        className={`cursor-pointer transition-all hover:shadow-md ${
                          selectedServiceId === service.knowledge_service_id
                            ? "border-primary bg-primary/5"
                            : "hover:bg-accent/50"
                        }`}
                        onClick={() =>
                          handleServiceSelect(service.knowledge_service_id)
                        }
                      >
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">
                              {service.name}
                            </CardTitle>
                            {selectedServiceId ===
                              service.knowledge_service_id && (
                              <Badge variant="default" className="text-xs">
                                Selected
                              </Badge>
                            )}
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="text-xs text-muted-foreground">
                            {service.description}
                          </p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </FieldGroup>
              {form.formState.errors.knowledge_service_id && (
                <FieldError>
                  {form.formState.errors.knowledge_service_id.message}
                </FieldError>
              )}
            </Field>

            {/* Main Prompt */}
            <Field>
              <Label htmlFor="prompt">Main Prompt</Label>
              <Textarea
                id="prompt"
                placeholder="Describe what you want to extract from the documents..."
                className={`min-h-[120px] ${
                  form.formState.errors.prompt ? "border-red-500" : ""
                }`}
                {...form.register("prompt")}
              />
              <FieldDescription>
                Instructions for the AI service on what to extract or analyze
              </FieldDescription>
              {form.formState.errors.prompt && (
                <FieldError>{form.formState.errors.prompt.message}</FieldError>
              )}
            </Field>

            {/* Example Prompts */}
            <Field>
              <Label>Example Prompts</Label>
              <FieldGroup>
                <div className="grid gap-2 md:grid-cols-2">
                  {EXAMPLE_PROMPTS.map((example, index) => (
                    <Button
                      key={index}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-auto p-3 text-left justify-start min-h-[60px]"
                      onClick={() => handleExamplePrompt(example.prompt)}
                    >
                      <div className="w-full">
                        <div className="font-medium text-xs mb-1">
                          {example.name}
                        </div>
                        <div
                          className="text-xs text-muted-foreground leading-relaxed overflow-hidden"
                          style={{
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                          }}
                        >
                          {example.prompt.substring(0, 120)}
                        </div>
                      </div>
                    </Button>
                  ))}
                </div>
              </FieldGroup>
              <FieldDescription>
                Click any example to use it as a starting point
              </FieldDescription>
            </Field>

            {/* Assistant Prompt (Optional) */}
            <Field>
              <Label htmlFor="assistant_prompt">
                Assistant Prompt (Optional)
              </Label>
              <Textarea
                id="assistant_prompt"
                placeholder="Additional formatting or style instructions..."
                className={`min-h-[80px] ${
                  form.formState.errors.assistant_prompt ? "border-red-500" : ""
                }`}
                {...form.register("assistant_prompt")}
              />
              <FieldDescription>
                Additional instructions for response formatting or style
              </FieldDescription>
              {form.formState.errors.assistant_prompt && (
                <FieldError>
                  {form.formState.errors.assistant_prompt.message}
                </FieldError>
              )}
            </Field>

            {/* Metadata (Advanced) */}
            <Field>
              <Label htmlFor="query_metadata">Metadata (Advanced)</Label>
              <Textarea
                id="query_metadata"
                placeholder='{"temperature": 0.2, "max_tokens": 1000}'
                className={`min-h-[60px] font-mono text-sm ${
                  form.formState.errors.query_metadata ? "border-red-500" : ""
                }`}
                {...form.register("query_metadata")}
              />
              <FieldDescription>
                Optional JSON configuration for the knowledge service (e.g.,
                temperature, max_tokens)
              </FieldDescription>
              {form.formState.errors.query_metadata && (
                <FieldError>
                  {form.formState.errors.query_metadata.message}
                </FieldError>
              )}
            </Field>
          </FieldSet>

          {/* Action Buttons */}
          <div className="flex gap-4 pt-4">
            <Button
              type="submit"
              disabled={createQueryMutation.isPending}
              className="flex-1 md:flex-initial"
            >
              {createQueryMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Query"
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={createQueryMutation.isPending}
            >
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
