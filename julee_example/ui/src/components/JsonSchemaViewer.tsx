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
import "./JsonSchemaViewer.css";

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

  const formatJsonSchema = (schema: Record<string, unknown>) => {
    return JSON.stringify(schema, null, 2);
  };

  const handleFormuleStateChange = useCallback(
    (newState: { schema?: Record<string, unknown> }) => {
      // Read-only component - no state changes needed
      if (newState?.schema) {
        try {
          // Schema viewed - no logging in production
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
