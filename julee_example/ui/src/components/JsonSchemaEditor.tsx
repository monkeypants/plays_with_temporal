"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import {
  FormuleContext,
  SchemaPreview,
  initFormuleSchema,
} from "react-formule";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code2, FileJson } from "lucide-react";
import CustomAiChat from "./CustomAiChat";
import CustomSelectOrEdit from "./CustomSelectOrEdit";
import KnowledgeServiceQueryDisplay from "./KnowledgeServiceQueryDisplay";

interface JsonSchemaEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  label?: string;
  description?: string;
  error?: string;
  knowledgeServiceQueries?: Record<string, string>;
  onFieldSelect?: (jsonPointer: string) => void;
  onUpdateQuery?: (jsonPointer: string, queryId: string | null) => void;
}

export default function JsonSchemaEditor({
  value = "{}",
  onChange,
  label = "Data to assemble",
  description,
  error,
  knowledgeServiceQueries = {},
  onFieldSelect: _onFieldSelect,
  onUpdateQuery = () => {},
}: JsonSchemaEditorProps) {
  const [activeTab, setActiveTab] = useState("builder");
  const [currentSchema, setCurrentSchema] = useState<string>("{}");
  // Parse current schema for AI chat component
  const parsedSchema = useMemo(() => {
    try {
      return JSON.parse(currentSchema);
    } catch {
      return {};
    }
  }, [currentSchema]);

  // Initialize formule only once on mount with the initial value
  useEffect(() => {
    try {
      const parsedSchema = JSON.parse(value);
      if (parsedSchema && typeof parsedSchema === "object") {
        initFormuleSchema(parsedSchema);
      } else {
        initFormuleSchema();
      }
    } catch {
      // If invalid JSON, initialize with empty schema
      initFormuleSchema();
    }
  }, []); // Empty dependency array = only run on mount

  // Handle formule state changes
  const handleFormuleStateChange = useCallback(
    (state: { current?: { schema?: unknown } }) => {
      if (state?.current?.schema) {
        try {
          const schemaString = JSON.stringify(state.current.schema, null, 2);
          setCurrentSchema(schemaString);
          if (onChange) {
            onChange(schemaString);
          }
        } catch (err) {
          console.error("Error serializing schema:", err);
        }
      }
    },
    [onChange],
  );

  return (
    <div className="space-y-4">
      {/* Label and Description */}
      <div>
        {label && <Label className="text-base font-medium">{label}</Label>}
        {description && (
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        )}
      </div>

      {/* Error Message */}
      {error && <div className="text-sm text-red-600 font-medium">{error}</div>}

      {/* Main Editor */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Data format</CardTitle>
          <CardDescription>
            Define the structure and fields of data you want to extract from
            documents. You can drag field types from the left panel to build
            your data structure in the right panel. Or you can simply ask an AI
            agent to do it for you with a prompt below - you will be shown the
            changes it proposes and can accept or reject them.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FormuleContext
            synchronizeState={handleFormuleStateChange}
            theme={{
              token: {
                colorPrimary: "#3b82f6", // Blue primary color to match UI
              },
            }}
          >
            <style>{`
              /* Hide form diff tab in AI component */
              .ant-tabs-tab:first-child {
                display: none !important;
              }
              /* Make schema diff tab active by default */
              .ant-tabs-tab:nth-child(2) .ant-tabs-tab-btn {
                color: #1890ff !important;
              }
            `}</style>
            {/* Custom AI Chat Component */}
            <div className="mb-4 border rounded-lg p-4">
              <CustomAiChat
                onSchemaChange={(newSchema) => {
                  initFormuleSchema({ schema: newSchema });
                  const schemaString = JSON.stringify(newSchema, null, 2);
                  if (onChange) {
                    onChange(schemaString);
                  }
                }}
                currentSchema={parsedSchema}
              />
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger
                  value="builder"
                  className="flex items-center gap-2"
                >
                  <Code2 className="h-4 w-4" />
                  Schema Builder
                </TabsTrigger>
                <TabsTrigger value="json" className="flex items-center gap-2">
                  <FileJson className="h-4 w-4" />
                  JSON Schema
                </TabsTrigger>
              </TabsList>

              <TabsContent value="builder" className="mt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="min-h-[400px] border rounded-lg p-4">
                    <h3 className="text-sm font-medium mb-3">Add Fields</h3>
                    <CustomSelectOrEdit
                      knowledgeServiceQueries={knowledgeServiceQueries}
                      onUpdateQuery={onUpdateQuery}
                    />
                  </div>
                  <div className="min-h-[400px] border rounded-lg p-4">
                    <h3 className="text-sm font-medium mb-3">
                      Schema Structure
                    </h3>
                    <SchemaPreview hideSchemaKey={false} />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="json" className="mt-4">
                <div className="min-h-[400px] border rounded-lg p-4">
                  <pre className="text-sm bg-gray-50 dark:bg-gray-900 p-4 rounded overflow-auto max-h-96">
                    <code>{currentSchema}</code>
                  </pre>
                </div>
              </TabsContent>
            </Tabs>
          </FormuleContext>
        </CardContent>
      </Card>

      {/* Knowledge Service Queries Display */}
      <KnowledgeServiceQueryDisplay
        knowledgeServiceQueries={knowledgeServiceQueries}
        jsonSchema={parsedSchema}
        onFieldSelect={(jsonPointer) => {
          // Try DOM simulation approach - find and click the field in schema tree
          if (!jsonPointer || jsonPointer === "/") return;

          const pathParts = jsonPointer.split("/").filter(Boolean);
          if (pathParts.length >= 2 && pathParts[0] === "properties") {
            const fieldId = pathParts[1];

            // Wait a moment, then find the field
            setTimeout(() => {
              // Try to find the field element in the schema tree
              // Look for elements containing the field name
              const possibleSelectors = [
                `[data-field-id="${fieldId}"]`,
                `[data-id="${fieldId}"]`,
                `[title="${fieldId}"]`,
                `.field-${fieldId}`,
                `#field-${fieldId}`,
                `[data-node-key="${fieldId}"]`,
                `[data-key="${fieldId}"]`,
              ];

              let fieldElement = null;
              for (const selector of possibleSelectors) {
                fieldElement = document.querySelector(selector);
                if (fieldElement) {
                  break;
                }
              }

              // If specific selectors don't work, try text content search
              if (!fieldElement) {
                // Limit search to schema tree container for performance
                const schemaContainer = document.querySelector(
                  ".ant-formule-container, .formule-container, .schema-preview",
                );
                const searchScope = schemaContainer || document;
                const allElements = searchScope.querySelectorAll("*");
                for (const element of allElements) {
                  if (
                    element.textContent?.includes(fieldId) &&
                    element.textContent.trim() === fieldId
                  ) {
                    fieldElement = element;
                    break;
                  }
                }
              }

              if (fieldElement) {
                // Scroll element into view first
                fieldElement.scrollIntoView({
                  behavior: "smooth",
                  block: "center",
                });

                // Try different click methods
                if (fieldElement.click) {
                  fieldElement.click();
                } else {
                  // Manual event dispatch
                  const clickEvent = new MouseEvent("click", {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                  });
                  fieldElement.dispatchEvent(clickEvent);
                }
              }
            }, 300); // Wait 300ms for animations
          }
        }}
      />
    </div>
  );
}
