"use client";

import React from "react";
import { useSelector } from "react-redux";
import { get } from "lodash-es";
import { useQuery } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  FileText,
  Type,
  Hash,
  ToggleLeft,
  Calendar,
  List,
  Settings,
  Database,
  Search,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import jsonpointer from "jsonpointer";

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

interface CustomPropertyViewerProps {
  knowledgeServiceQueries?: Record<string, string>;
}

const getTypeIcon = (type: string) => {
  switch (type) {
    case "string":
      return <Type className="h-4 w-4" />;
    case "number":
    case "integer":
      return <Hash className="h-4 w-4" />;
    case "boolean":
      return <ToggleLeft className="h-4 w-4" />;
    case "array":
      return <List className="h-4 w-4" />;
    case "object":
      return <FileText className="h-4 w-4" />;
    default:
      return <FileText className="h-4 w-4" />;
  }
};

const getTypeColor = (type: string) => {
  switch (type) {
    case "string":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    case "number":
    case "integer":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "boolean":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
    case "array":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
    case "object":
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
  }
};

export default function CustomPropertyViewer({
  knowledgeServiceQueries = {},
}: CustomPropertyViewerProps) {
  // Get field information from Redux state (same as CustomPropertyEditor)
  const path = useSelector(
    (state: unknown) => (state as any).schemaWizard.field.path,
  );
  const uiPath = useSelector(
    (state: unknown) => (state as any).schemaWizard.field.uiPath,
  );

  const schema = useSelector((state: unknown) =>
    path
      ? get((state as any).schemaWizard, ["current", "schema", ...path])
      : null,
  );

  // Get field title from schema
  const fieldTitle = schema?.title || "";

  // Determine field name
  const fieldName = React.useMemo(() => {
    if (!path || path.length === 0) {
      return "root";
    }

    try {
      // 'properties' and 'items' are JSON Schema keywords used to traverse object and array structures.
      // We filter them out to extract the actual field name, since they do not represent user-defined fields.
      const name = path.findLast(
        (item: string) => item !== "properties" && item !== "items",
      );
      return name || "root";
    } catch (error) {
      console.warn("Error computing field name from path:", path, error);
      return "root";
    }
  }, [path]);

  // Create breadcrumb display
  const renderBreadcrumb = () => {
    if (!path || path.length === 0) return "Root";

    try {
      const breadcrumbParts = [];
      let currentName = "";

      for (const item of path) {
        if (item === "properties") {
          breadcrumbParts.push(`{ } ${currentName}`.trim());
          currentName = "";
        } else if (item === "items") {
          breadcrumbParts.push(`[ ] ${currentName}`.trim());
          currentName = "";
        } else {
          currentName = item;
        }
      }

      if (currentName) {
        breadcrumbParts.push(currentName);
      }

      return breadcrumbParts.join(" → ");
    } catch (error) {
      console.warn("Error creating breadcrumb from path:", path, error);
      return "Root";
    }
  };

  // Create JSON pointer path for knowledge service queries (matches KnowledgeServiceSection)
  const jsonPointerPath = React.useMemo(() => {
    if (!path || path.length === 0) return "/";

    // Safely join path elements
    try {
      const result = "/" + path.join("/");
      return result;
    } catch (error) {
      console.warn("Error creating JSON pointer from path:", path, error);
      return "/";
    }
  }, [path, knowledgeServiceQueries]);

  const queryId =
    jsonPointerPath && jsonPointerPath !== "/" && path && path.length > 0
      ? knowledgeServiceQueries[jsonPointerPath]
      : null;

  // Fetch query details if there's a linked query
  const { data: queryData } = useQuery({
    queryKey: ["query", queryId],
    queryFn: async (): Promise<KnowledgeServiceQuery> => {
      const response = await apiClient.get(
        `/knowledge_service_queries/${queryId}`,
      );
      return response.data;
    },
    enabled: !!queryId,
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  });

  if (!path || path.length === 0 || !schema) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Property Details
          </CardTitle>
          <CardDescription>
            Select a field from the schema structure to view its properties
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <Calendar className="h-16 w-16 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium mb-2">No field selected</p>
            <p className="text-sm">
              Click on any field in the schema structure to see its details and
              query mappings
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getTypeIcon(schema.type)}
          {fieldTitle || fieldName}
        </CardTitle>
        <CardDescription className="font-mono text-sm">
          {renderBreadcrumb()}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Basic Properties */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-sm font-medium text-muted-foreground">
                Field Name
              </Label>
              <p className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                {fieldName}
              </p>
            </div>
            <div>
              <Label className="text-sm font-medium text-muted-foreground">
                Type
              </Label>
              <div className="mt-1">
                <Badge className={getTypeColor(schema.type)}>
                  {schema.type}
                </Badge>
              </div>
            </div>
          </div>

          {fieldTitle && (
            <div>
              <Label className="text-sm font-medium text-muted-foreground">
                Title
              </Label>
              <p className="mt-1 text-sm">{fieldTitle}</p>
            </div>
          )}

          {schema.description && (
            <div>
              <Label className="text-sm font-medium text-muted-foreground">
                Description
              </Label>
              <p className="mt-1 text-sm text-muted-foreground">
                {schema.description}
              </p>
            </div>
          )}
        </div>

        {/* Type-specific Properties */}
        {schema.type === "string" && (
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-foreground border-b pb-2">
              String Properties
            </h4>
            {schema.minLength !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Minimum Length
                </Label>
                <p className="mt-1 text-sm">{schema.minLength}</p>
              </div>
            )}
            {schema.maxLength !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Maximum Length
                </Label>
                <p className="mt-1 text-sm">{schema.maxLength}</p>
              </div>
            )}
            {schema.pattern && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Pattern
                </Label>
                <p className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {schema.pattern}
                </p>
              </div>
            )}
          </div>
        )}

        {(schema.type === "number" || schema.type === "integer") && (
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-foreground border-b pb-2">
              Number Properties
            </h4>
            {schema.minimum !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Minimum
                </Label>
                <p className="mt-1 text-sm">{schema.minimum}</p>
              </div>
            )}
            {schema.maximum !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Maximum
                </Label>
                <p className="mt-1 text-sm">{schema.maximum}</p>
              </div>
            )}
            {schema.multipleOf !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Multiple Of
                </Label>
                <p className="mt-1 text-sm">{schema.multipleOf}</p>
              </div>
            )}
          </div>
        )}

        {schema.type === "array" && schema.items && (
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-foreground border-b pb-2">
              Array Properties
            </h4>
            <div>
              <Label className="text-sm font-medium text-muted-foreground">
                Item Type
              </Label>
              <div className="mt-1">
                <Badge className={getTypeColor(schema.items.type || "unknown")}>
                  {schema.items.type || "unknown"}
                </Badge>
              </div>
            </div>
            {schema.minItems !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Minimum Items
                </Label>
                <p className="mt-1 text-sm">{schema.minItems}</p>
              </div>
            )}
            {schema.maxItems !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Maximum Items
                </Label>
                <p className="mt-1 text-sm">{schema.maxItems}</p>
              </div>
            )}
          </div>
        )}

        {schema.type === "object" && schema.properties && (
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-foreground border-b pb-2">
              Object Properties
            </h4>
            <div>
              <Label className="text-sm font-medium text-muted-foreground">
                Properties Count
              </Label>
              <p className="mt-1 text-sm">
                {typeof schema.properties === "object" &&
                schema.properties !== null
                  ? Object.keys(schema.properties).length
                  : 0}
              </p>
            </div>
            {schema.required && schema.required.length > 0 && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Required Properties
                </Label>
                <div className="mt-1 flex flex-wrap gap-2">
                  {schema.required.map((prop: string, index: number) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {prop}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {schema.enum && (
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-foreground border-b pb-2">
              Allowed Values
            </h4>
            <div className="flex flex-wrap gap-2">
              {schema.enum.map((value: any, index: number) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {String(value)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Validation Properties */}
        {(schema.const !== undefined || schema.default !== undefined) && (
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-foreground border-b pb-2">
              Validation
            </h4>
            {schema.const !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Constant Value
                </Label>
                <p className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {String(schema.const)}
                </p>
              </div>
            )}
            {schema.default !== undefined && (
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Default Value
                </Label>
                <p className="mt-1 text-sm font-mono bg-muted px-2 py-1 rounded">
                  {String(schema.default)}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Knowledge Service Query Mapping */}
        {queryId && (
          <Card className="border-l-4 border-l-blue-500">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Search className="h-4 w-4 text-blue-600" />
                Associated Query
              </CardTitle>
              <CardDescription>
                This field will be populated by data extracted using the linked
                knowledge service query
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {queryData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">
                        Query Name
                      </Label>
                      <p className="mt-1 text-sm font-medium">
                        {queryData.name}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">
                        Knowledge Service
                      </Label>
                      <p className="mt-1 text-sm">
                        {queryData.knowledge_service_id}
                      </p>
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">
                      Query ID
                    </Label>
                    <div className="mt-1">
                      <Badge variant="secondary" className="font-mono text-xs">
                        {queryId}
                      </Badge>
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">
                      Prompt
                    </Label>
                    <div className="mt-1 p-3 bg-muted rounded-md">
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                        {queryData.prompt}
                      </p>
                    </div>
                  </div>

                  {queryData.assistant_prompt && (
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">
                        Assistant Prompt
                      </Label>
                      <div className="mt-1 p-3 bg-muted rounded-md">
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                          {queryData.assistant_prompt}
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="pt-2 border-t">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <ExternalLink className="h-3 w-3" />
                      <span>
                        Created:{" "}
                        {new Date(queryData.created_at).toLocaleDateString()}
                      </span>
                      <span>•</span>
                      <span>
                        Updated:{" "}
                        {new Date(queryData.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">
                      Query ID
                    </Label>
                    <div className="mt-1">
                      <Badge variant="secondary" className="font-mono text-xs">
                        {queryId}
                      </Badge>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Loading query details...
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Raw Properties (for debugging/advanced users) */}
        {Object.keys(schema).length > 3 && (
          <details className="space-y-2">
            <summary className="text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground">
              Advanced: Raw Property Definition
            </summary>
            <div className="mt-2 bg-muted p-3 rounded-md">
              <pre className="text-xs overflow-auto">
                {JSON.stringify(schema, null, 2)}
              </pre>
            </div>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
