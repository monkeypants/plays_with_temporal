"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FormuleContext,
  SelectOrEdit,
  SchemaPreview,
  FormPreview,
  initFormuleSchema,
} from "react-formule";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code2, FileJson } from "lucide-react";

interface JsonSchemaEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  label?: string;
  description?: string;
  error?: string;
}

export default function JsonSchemaEditor({
  value = "{}",
  onChange,
  label = "Data to assemble",
  description,
  error,
}: JsonSchemaEditorProps) {
  const [activeTab, setActiveTab] = useState("builder");
  const [currentSchema, setCurrentSchema] = useState<string>("{}");

  // Initialize formule with existing schema if provided
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
  }, [value]);

  // Handle formule state changes
  const handleFormuleStateChange = useCallback(
    (state: any) => {
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
            documents. Drag field types from the left panel to build your data
            structure in the right panel.
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
            customFieldTypes={(() => {
              const customFieldTypes = {
                collections: {
                  object: {
                    title: "Object",
                    icon: <span>&#123;&nbsp;&#125;</span>,
                    description: "Group of fields, useful for nesting",
                    child: {},
                    default: {
                      schema: {
                        type: "object",
                        properties: {},
                      },
                      uiSchema: {},
                    },
                  },
                  array: {
                    title: "List",
                    icon: <span>[ ]</span>,
                    description:
                      "List of fields supporting addition, deletion and reordering",
                    child: {},
                    default: {
                      schema: {
                        type: "array",
                        items: {},
                      },
                      uiSchema: {},
                    },
                  },
                },
                simple: {
                  text: {
                    title: "Text",
                    icon: <span>T</span>,
                    description: "Text field supporting validation",
                    child: {},
                    default: {
                      schema: {
                        type: "string",
                      },
                      uiSchema: {
                        "ui:widget": "text",
                      },
                    },
                  },
                  number: {
                    title: "Number",
                    icon: <span>#</span>,
                    description: "Number field (integer or float)",
                    child: {},
                    default: {
                      schema: {
                        type: "number",
                      },
                      uiSchema: {},
                    },
                  },
                },
                advanced: {},
              };

              // Hide unwanted default fields by overriding with empty objects
              const hiddenField = {
                title: "",
                icon: <span></span>,
                description: "",
                child: {},
                default: { schema: {}, uiSchema: {} },
              };

              customFieldTypes.collections = {
                ...customFieldTypes.collections,
                accordion: hiddenField,
                layer: hiddenField,
                tabView: hiddenField,
                stepsView: hiddenField,
              };

              customFieldTypes.simple = {
                ...customFieldTypes.simple,
                textarea: hiddenField,
                checkbox: hiddenField,
                switch: hiddenField,
                radio: hiddenField,
                select: hiddenField,
                date: hiddenField,
                email: hiddenField,
              };

              customFieldTypes.advanced = {
                uri: hiddenField,
                richeditor: hiddenField,
                tags: hiddenField,
                idFetcher: hiddenField,
                codeEditor: hiddenField,
                file: hiddenField,
                slider: hiddenField,
                slider_markers: hiddenField,
              };

              return customFieldTypes;
            })()}
          >
            {/* Hide Advanced fields section with simpler CSS */}
            <style>{`
              .ant-collapse-item:nth-child(3) {
                display: none !important;
              }
            `}</style>
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
                    <SelectOrEdit />
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
    </div>
  );
}
