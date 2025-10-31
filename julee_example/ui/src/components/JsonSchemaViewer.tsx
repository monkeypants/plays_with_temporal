"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code2, FileJson } from "lucide-react";
import {
  FormuleContext,
  SchemaPreview,
  initFormuleSchema,
} from "react-formule";
import CustomPropertyViewer from "./CustomPropertyViewer";
import KnowledgeServiceQueryDisplay from "./KnowledgeServiceQueryDisplay";

interface JsonSchemaViewerProps {
  schema: Record<string, unknown>;
  knowledgeServiceQueries?: Record<string, string>;
}

export default function JsonSchemaViewer({
  schema,
  knowledgeServiceQueries = {},
}: JsonSchemaViewerProps) {
  const rootProperties = useMemo(() => {
    return (schema.properties as Record<string, unknown>) || {};
  }, [schema]);

  const requiredFields = useMemo(() => {
    return (schema.required as string[]) || [];
  }, [schema]);

  const formatJsonSchema = (schema: Record<string, unknown>) => {
    return JSON.stringify(schema, null, 2);
  };

  const handleFormuleStateChange = useCallback(
    (newState: { schema?: Record<string, unknown> }) => {
      // Read-only component - no state changes needed
      if (newState?.schema) {
        try {
          console.log("Schema viewed:", newState.schema);
        } catch (err) {
          console.error("Error viewing schema:", err);
        }
      }
    },
    [],
  );

  // Initialize the schema in FormuleContext when component mounts
  useEffect(() => {
    if (schema && Object.keys(schema).length > 0) {
      initFormuleSchema({ schema });
    }
  }, [schema]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Code2 className="h-5 w-5" />
          JSON Schema & Query Mappings
        </CardTitle>
        <CardDescription>
          Schema structure and knowledge service query mappings
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Tabs defaultValue="tree" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="tree" className="flex items-center gap-2">
                <FileJson className="h-4 w-4" />
                Schema Tree
              </TabsTrigger>
              <TabsTrigger value="json" className="flex items-center gap-2">
                <Code2 className="h-4 w-4" />
                Raw JSON
              </TabsTrigger>
            </TabsList>

            <TabsContent value="tree" className="mt-4">
              <FormuleContext
                synchronizeState={handleFormuleStateChange}
                theme={{
                  token: {
                    colorPrimary: "#3b82f6",
                  },
                }}
              >
                <style>{`
                  /* Hide the schema key in read-only mode */
                  .formule-schema-key {
                    display: none !important;
                  }
                  /* Hide the entire drop zone container with icon and text */
                  .ant-space:has([data-cy="dropArea"]) {
                    display: none !important;
                  }
                  /* Fallback for browsers that don't support :has() */
                  [data-cy="dropArea"] {
                    display: none !important;
                  }
                  [data-cy="dropArea"] + .ant-space-item {
                    display: none !important;
                  }
                  /* Hide the parent container by style attributes */
                  .ant-space[style*="border: 1px solid lightgrey"] {
                    display: none !important;
                  }
                  /* Hide settings cog icons */
                  .ant-btn[title*="settings"],
                  .ant-btn[title*="Settings"],
                  .anticon-setting {
                    display: none !important;
                  }
                  /* Disable drag functionality but keep click interactions */
                  [draggable="true"] {
                    -webkit-user-drag: none !important;
                    -khtml-user-drag: none !important;
                    -moz-user-drag: none !important;
                    -o-user-drag: none !important;
                    user-drag: none !important;
                    cursor: pointer !important;
                  }
                  /* Make clickable items show pointer cursor */
                  .formule-field-item,
                  .formule-field,
                  [role="button"],
                  .ant-btn {
                    cursor: pointer !important;
                    pointer-events: auto !important;
                  }
                  /* Allow text selection */
                  .ant-typography,
                  span {
                    user-select: text !important;
                  }
                  /* Hide field type selector in read-only mode */
                  .formule-field-type-selector,
                  .ant-select[placeholder*="field type"] {
                    display: none !important;
                  }
                  /* Hide add/remove buttons */
                  .ant-btn[title*="add"],
                  .ant-btn[title*="remove"],
                  .ant-btn[title*="delete"] {
                    display: none !important;
                  }
                `}</style>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="min-h-[400px]">
                    <CustomPropertyViewer
                      knowledgeServiceQueries={knowledgeServiceQueries}
                    />
                  </div>
                  <div className="min-h-[400px] border rounded-lg p-4">
                    <h3 className="text-sm font-medium mb-3">
                      Schema Structure
                    </h3>
                    <SchemaPreview hideSchemaKey={true} />
                  </div>
                </div>
              </FormuleContext>
            </TabsContent>

            <TabsContent value="json" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Code2 className="h-5 w-5" />
                    Raw JSON Schema
                  </CardTitle>
                  <CardDescription>
                    The complete JSON schema definition
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-muted p-4 rounded-md overflow-auto max-h-96">
                    <pre className="text-sm font-mono">
                      {formatJsonSchema(schema)}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </CardContent>

      {/* Knowledge Service Queries Overview - Full Width */}
      <div className="border-t pt-6 px-6 pb-6">
        <KnowledgeServiceQueryDisplay
          knowledgeServiceQueries={knowledgeServiceQueries}
          jsonSchema={schema}
        />
      </div>
    </Card>
  );
}
