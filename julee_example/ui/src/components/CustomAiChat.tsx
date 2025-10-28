"use client";

import { useState } from "react";
import { diffLines } from "diff";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send } from "lucide-react";

interface CustomAiChatProps {
  onSchemaChange: (schema: object) => void;
  currentSchema: object;
}

interface ProposedChanges {
  schema: object;
  prompt: string;
}

export default function CustomAiChat({
  onSchemaChange,
  currentSchema,
}: CustomAiChatProps) {
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [proposedChanges, setProposedChanges] =
    useState<ProposedChanges | null>(null);
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
    if (proposedChanges) {
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
}
