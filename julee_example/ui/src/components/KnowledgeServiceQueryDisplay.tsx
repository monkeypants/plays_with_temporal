"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink, Search, AlertCircle } from "lucide-react";
import jsonpointer from "jsonpointer";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

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

interface KnowledgeServiceMapping {
  [jsonPointer: string]: string;
}

interface KnowledgeServiceQueryDisplayProps {
  knowledgeServiceQueries: KnowledgeServiceMapping;
  jsonSchema: Record<string, unknown>;
  onFieldSelect?: (jsonPointer: string) => void;
}

/**
 * Gets field information from JSON schema using JSON pointer
 * @param jsonPointer - JSON pointer like "/properties/companyName"
 * @param schema - The JSON schema object
 * @returns Object with field name and description
 */
const getFieldInfo = (jsonPointer: string, schema: Record<string, unknown>) => {
  if (!jsonPointer || jsonPointer === "" || jsonPointer === "/") {
    return {
      name: schema.title || "Root Schema",
      description: schema.description || "Root of the schema",
    };
  }

  try {
    const fieldSchema = jsonpointer.get(schema, jsonPointer);
    if (fieldSchema && typeof fieldSchema === "object") {
      // Extract field name from JSON pointer as fallback
      const pathParts = jsonPointer.split("/").filter(Boolean);
      const fieldName = pathParts[pathParts.length - 1] || "field";

      return {
        name: fieldSchema.title || fieldName,
        description: fieldSchema.description || "No description available",
      };
    }
  } catch (error) {
    console.warn(
      `Could not resolve JSON pointer ${jsonPointer} in schema:`,
      error,
    );
  }

  // Extract field name from JSON pointer for fallback
  const pathParts = jsonPointer.split("/").filter(Boolean);
  const fieldName = pathParts[pathParts.length - 1] || "field";

  return {
    name: fieldName,
    description: "Field not found in current schema",
  };
};

export default function KnowledgeServiceQueryDisplay({
  knowledgeServiceQueries = {},
  jsonSchema = {},
  onFieldSelect,
}: KnowledgeServiceQueryDisplayProps) {
  const mappingEntries = Object.entries(knowledgeServiceQueries);

  // Get unique query IDs from the mappings
  const queryIds = [...new Set(Object.values(knowledgeServiceQueries))];

  // Fetch only the specific queries we need
  const { data: queriesData } = useQuery({
    queryKey: ["queries", queryIds.sort().join(",")],
    queryFn: async (): Promise<QueriesResponse> => {
      if (queryIds.length === 0) {
        return { items: [], total: 0, page: 1, size: 0, pages: 0 };
      }
      const idsParam = queryIds.join(",");
      const response = await apiClient.get(
        `/knowledge_service_queries/?ids=${idsParam}`,
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
    enabled: queryIds.length > 0, // Only run query if we have IDs to fetch
  });

  // Create a lookup map for quick query access
  const queryLookup =
    queriesData?.items.reduce(
      (acc, query) => {
        acc[query.query_id] = query;
        return acc;
      },
      {} as Record<string, KnowledgeServiceQuery>,
    ) || {};

  const getQueryInfo = (queryId: string) => {
    const query = queryLookup[queryId];
    if (!query) {
      console.warn(`Query not found: ${queryId}`);
      return {
        name: `Query ${queryId} (not found)`,
        description: `Query ${queryId} could not be loaded`,
      };
    }
    return {
      name: query.name,
      description: query.prompt,
    };
  };

  if (mappingEntries.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Search className="h-4 w-4" />
            Knowledge Service Queries
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertCircle className="h-8 w-8 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground mb-2">
              No knowledge service queries configured
            </p>
            <p className="text-xs text-muted-foreground max-w-md">
              Fields can be associated with specific queries to extract targeted
              data. Use the field property editor to associate a query with that
              field.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Search className="h-4 w-4" />
          Knowledge Service Queries
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground mb-4">
          Click any mapping to edit that field in the property editor
        </p>

        <div className="space-y-2">
          {mappingEntries.map(([jsonPointer, queryId]) => {
            const fieldInfo = getFieldInfo(jsonPointer, jsonSchema);
            const queryInfo = getQueryInfo(queryId);

            return (
              <div
                key={jsonPointer}
                className={`
                  border rounded-lg p-3 transition-colors
                  ${
                    onFieldSelect
                      ? "cursor-pointer hover:bg-accent/50 hover:border-primary/20"
                      : ""
                  }
                `}
                onClick={() => onFieldSelect?.(jsonPointer)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">
                        {fieldInfo.name}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        Field
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-muted-foreground">→</span>
                      <span className="text-sm text-primary font-medium">
                        {queryInfo.name}
                      </span>
                      <Badge variant="secondary" className="text-xs">
                        Query
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mb-1">
                      {fieldInfo.description}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Query: {queryInfo.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 font-mono">
                      {jsonPointer || "/"}
                    </p>
                  </div>

                  {onFieldSelect && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0 h-8 w-8 p-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        onFieldSelect(jsonPointer);
                      }}
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span className="sr-only">Edit field</span>
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 pt-3 border-t">
          <p className="text-xs text-muted-foreground">
            {mappingEntries.length} field
            {mappingEntries.length !== 1 ? "s" : ""} associated with queries
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
