"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import { diffLines } from "diff";
import {
  FormuleContext,
  SelectOrEdit,
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code2, FileJson, Send } from "lucide-react";

// Custom AI Chat Component
const CustomAiChat = ({
  onSchemaChange,
  currentSchema,
}: {
  onSchemaChange: (schema: object) => void;
  currentSchema: object;
}) => {
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [proposedChanges, setProposedChanges] = useState<{
    schema: object;
    prompt: string;
  } | null>(null);
  const [error, setError] = useState("");

  const generateSchema = async () => {
    if (!prompt.trim()) return;

    setIsGenerating(true);
    setError("");

    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${import.meta.env.VITE_GEMINI_API_KEY}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            contents: [
              {
                parts: [
                  {
                    text: `You are a JSON Schema expert. Generate only JSON schemas, no UI schemas. Return JSON with only a 'schema' property containing the JSON Schema.

Create a JSON schema for: ${prompt}. Current schema: ${JSON.stringify(currentSchema)}. Return only the schema property as valid JSON.`,
                  },
                ],
              },
            ],
            generationConfig: {
              response_mime_type: "application/json",
            },
          }),
        },
      );

      const data = await response.json();

      // Validate response structure
      if (
        data &&
        Array.isArray(data.candidates) &&
        data.candidates.length > 0 &&
        data.candidates[0].content &&
        Array.isArray(data.candidates[0].content.parts) &&
        data.candidates[0].content.parts.length > 0 &&
        typeof data.candidates[0].content.parts[0].text === "string"
      ) {
        let content;
        try {
          content = JSON.parse(data.candidates[0].content.parts[0].text);
        } catch (parseErr) {
          setError(
            "Failed to parse schema JSON: " +
              (parseErr instanceof Error
                ? parseErr.message
                : "Unknown parsing error"),
          );
          setIsGenerating(false);
          return;
        }

        setProposedChanges({
          schema: content.schema || content,
          prompt: prompt,
        });
        setPrompt("");
      } else {
        setError("Unexpected response structure from API.");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unknown error occurred",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApply = () => {
    if (proposedChanges && onSchemaChange) {
      onSchemaChange(proposedChanges.schema);
    }
    setProposedChanges(null);
  };

  const handleReject = () => {
    setProposedChanges(null);
  };

  return (
    <div className="space-y-4">
      {/* Chat Input */}
      <div className="flex gap-2">
        <Input
          placeholder="Describe the data structure you want to create..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyPress={(e) =>
            e.key === "Enter" && !isGenerating && generateSchema()
          }
          className="flex-1"
        />
        <Button
          onClick={generateSchema}
          disabled={isGenerating || !prompt.trim()}
          size="sm"
        >
          {isGenerating ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="text-red-600 text-sm p-2 bg-red-50 rounded">
          Error: {error}
        </div>
      )}

      {/* Schema Diff */}
      {proposedChanges && (
        <div className="border rounded-lg p-4 bg-gray-50">
          <h3 className="font-medium mb-3">Proposed Schema Changes</h3>
          <div className="text-sm mb-3 text-gray-600 break-words">
            Request: "{proposedChanges.prompt}"
          </div>

          <div className="mb-3">
            <div className="border rounded bg-white overflow-hidden">
              <div className="text-xs bg-gray-100 px-3 py-2 border-b font-mono">
                Schema Changes
              </div>
              <div className="overflow-auto max-h-64 w-full max-w-full">
                <table className="w-full table-fixed">
                  <tbody>
                    {diffLines(
                      JSON.stringify(currentSchema, null, 2),
                      JSON.stringify(proposedChanges.schema, null, 2),
                    ).map((part, index) => (
                      <tr key={index}>
                        <td className="w-8 px-2 py-0 text-center font-mono text-xs text-gray-400 bg-gray-50">
                          {part.added ? "+" : part.removed ? "-" : " "}
                        </td>
                        <td
                          className={`font-mono text-sm whitespace-pre px-2 py-0 ${
                            part.added
                              ? "bg-green-100 text-green-800"
                              : part.removed
                                ? "bg-red-100 text-red-800"
                                : ""
                          }`}
                          style={{
                            maxWidth: "0",
                            overflow: "auto",
                          }}
                        >
                          {part.value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleApply}
              size="sm"
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              Apply Changes
            </Button>
            <Button onClick={handleReject} variant="outline" size="sm">
              Reject
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

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
  // Parse current value for AI chat component
  const parsedSchema = useMemo(() => {
    if (value) {
      try {
        return JSON.parse(value);
      } catch {
        return {};
      }
    } else {
      return {};
    }
  }, [value]);

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
    (state: { current?: { schema?: unknown } }) => {
      if (state?.current?.schema) {
        try {
          const schemaString = JSON.stringify(state.current.schema, null, 2);
          setCurrentSchema(schemaString);
          setParsedSchema(state.current.schema);
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
            {/* TODO: Temporary CSS solution - will be replaced with custom FieldTypePicker component in next PR */}
            <style>{`
              .ant-collapse-item:nth-child(3) {
                display: none !important;
              }
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
