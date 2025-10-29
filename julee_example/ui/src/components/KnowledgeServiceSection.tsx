"use client";

import { useMemo, useState, useEffect } from "react";
import { useSelector } from "react-redux";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Search, Plus, ExternalLink, Trash2, ChevronDown } from "lucide-react";
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

/**
 * Converts field path array to JSON pointer string
 * @param path - Array of path segments like ["properties", "companyName"]
 * @returns JSON pointer string like "/properties/companyName"
 */
const pathToJsonPointer = (path: string[]): string => {
  if (!path || path.length === 0) return "/";
  return "/" + path.join("/");
};

interface KnowledgeServiceSectionProps {
  knowledgeServiceQueries: Record<string, string>;
  onUpdateQuery?: (jsonPointer: string, queryId: string | null) => void;
}

export default function KnowledgeServiceSection({
  knowledgeServiceQueries = {},
  onUpdateQuery = () => {},
}: KnowledgeServiceSectionProps) {
  // Local state for UI interaction
  const [showQueryUI, setShowQueryUI] = useState(false);

  // Get current field information from Redux
  const path = useSelector(
    (state: { schemaWizard: { field: { path: string[] } } }) =>
      state.schemaWizard.field.path,
  );

  // Generate JSON pointer for current field
  const jsonPointer = useMemo(() => pathToJsonPointer(path), [path]);

  // Derive state from current query mapping
  const currentQueryId = knowledgeServiceQueries[jsonPointer];
  const selectedQueryId = currentQueryId || "";

  // Update local state when field changes or query mapping changes
  const shouldShowQueryUI = useMemo(() => {
    return !!currentQueryId;
  }, [currentQueryId]);

  useEffect(() => {
    setShowQueryUI(shouldShowQueryUI);
  }, [shouldShowQueryUI]);

  // Fetch all available queries
  const { data: queriesData, isLoading: isLoadingQueries } = useQuery({
    queryKey: ["queries"],
    queryFn: async (): Promise<QueriesResponse> => {
      const response = await apiClient.get(
        "/knowledge_service_queries?size=100",
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  });

  const availableQueries = queriesData?.items || [];

  // Get field name for display
  const fieldName = useMemo(() => {
    if (!path || path.length === 0) return "root";
    // Find the last item that's not "properties" or "items"
    for (let i = path.length - 1; i >= 0; i--) {
      if (path[i] !== "properties" && path[i] !== "items") {
        return path[i];
      }
    }
    return "field";
  }, [path]);

  const handleCheckboxChange = (checked: boolean) => {
    setShowQueryUI(checked);
    if (!checked) {
      // Remove query association when unchecking
      onUpdateQuery(jsonPointer, null);
    }
    // When checking the box, we just show the UI - user will select query from dropdown
  };

  const handleQuerySelect = (queryId: string) => {
    onUpdateQuery(jsonPointer, queryId);
  };

  const handleRemoveQuery = () => {
    onUpdateQuery(jsonPointer, null);
  };

  const currentQuery = availableQueries.find(
    (q) => q.query_id === selectedQueryId,
  );

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Search className="h-4 w-4" />
          Associated query
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Checkbox to opt-in */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="has-query"
            checked={showQueryUI}
            onCheckedChange={(checked) => {
              handleCheckboxChange(checked === true);
            }}
          />
          <Label htmlFor="has-query" className="text-sm">
            Extract data for '{fieldName}' with a specific query
          </Label>
        </div>

        {/* Query selection (shown when checkbox is checked) */}
        {showQueryUI && (
          <div className="space-y-3 pl-6">
            <div>
              <Label className="text-sm font-medium">Query</Label>
              <div className="relative">
                <select
                  value={selectedQueryId}
                  onChange={(e) => handleQuerySelect(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm appearance-none pr-8"
                >
                  <option value="" disabled>
                    Select query...
                  </option>
                  {availableQueries.map((query) => (
                    <option key={query.query_id} value={query.query_id}>
                      {query.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              </div>
              {isLoadingQueries && (
                <p className="text-xs text-muted-foreground mt-1">
                  Loading queries...
                </p>
              )}
              <div className="mt-2 pt-2 border-t">
                <div className="px-2 py-1.5 text-sm text-muted-foreground flex items-center gap-2 cursor-pointer hover:bg-accent rounded-sm">
                  <Plus className="h-3 w-3" />
                  Create New Query
                </div>
              </div>
            </div>

            {/* Show current query info */}
            {currentQuery && (
              <div className="border rounded-lg p-3 bg-muted/30">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{currentQuery.name}</p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {currentQuery.prompt}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Service: {currentQuery.knowledge_service_id}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2">
              {selectedQueryId && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-1"
                    onClick={() => {
                      // TODO: Open edit modal in Phase 3
                    }}
                  >
                    <ExternalLink className="h-3 w-3" />
                    Edit Query
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-1 text-red-600 hover:text-red-700"
                    onClick={handleRemoveQuery}
                  >
                    <Trash2 className="h-3 w-3" />
                    Remove Link
                  </Button>
                </>
              )}
            </div>

            <div className="text-xs text-muted-foreground">
              ℹ This query will extract data for this specific field
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
