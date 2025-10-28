"use client";

import React, { useContext } from "react";
import { DndProvider, useDrag } from "react-dnd";
import { MultiBackend } from "react-dnd-multi-backend";
import { HTML5toTouch } from "rdndmb-html5-to-touch";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Braces, List, Type, Hash } from "lucide-react";

// Import CustomizationContext to get field definitions
let CustomizationContext: React.Context<any> | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  CustomizationContext =
    require("/home/michael/dev/3rdparty/react-formule/src/contexts/CustomizationContext").default;
} catch {
  console.warn("Could not import CustomizationContext from react-formule");
}

interface FieldTypeInfo {
  key: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  category: "collections" | "simple";
  data: {
    title: string;
    icon: React.ReactNode;
    description: string;
    child: Record<string, unknown>;
    default: {
      schema: Record<string, unknown>;
      uiSchema: Record<string, unknown>;
    };
  };
}

// Our 4 desired field types with custom icons
const CUSTOM_FIELD_TYPES: Omit<FieldTypeInfo, "data">[] = [
  {
    key: "object",
    title: "Object",
    description: "Group of fields, useful for nesting",
    icon: <Braces className="h-4 w-4" />,
    category: "collections",
  },
  {
    key: "array",
    title: "List",
    description: "List of fields supporting addition, deletion and reordering",
    icon: <List className="h-4 w-4" />,
    category: "collections",
  },
  {
    key: "text",
    title: "Text",
    description: "Text field supporting validation",
    icon: <Type className="h-4 w-4" />,
    category: "simple",
  },
  {
    key: "number",
    title: "Number",
    description: "Number field (integer or float)",
    icon: <Hash className="h-4 w-4" />,
    category: "simple",
  },
];

interface DraggableFieldCardProps {
  fieldType: FieldTypeInfo;
}

const DraggableFieldCard: React.FC<DraggableFieldCardProps> = ({
  fieldType,
}) => {
  const [{ isDragging }, drag] = useDrag({
    type: "FIELD_TYPE", // Use the same type as react-formule
    item: { data: fieldType.data },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const opacity = isDragging ? 0.4 : 1;

  return (
    <div
      ref={drag}
      style={{ opacity }}
      data-cy={`field-${fieldType.key}`} // Add data-cy for compatibility
    >
      <Card className="cursor-move transition-all hover:shadow-md hover:bg-accent/50 border-2 hover:border-primary/20">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <div className="shrink-0 mt-1 text-primary">{fieldType.icon}</div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-foreground mb-1">
                {fieldType.title}
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {fieldType.description}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const FieldTypePickerContent: React.FC = () => {
  // Always call useContext, but handle null context
  const customizationContext = useContext(
    CustomizationContext || React.createContext(null),
  );

  // Merge our custom definitions with react-formule's data
  const fieldTypes = React.useMemo((): FieldTypeInfo[] => {
    const result: FieldTypeInfo[] = [];

    for (const customType of CUSTOM_FIELD_TYPES) {
      let fieldData = null;

      // Try to get the actual field type data from CustomizationContext
      if (
        customizationContext &&
        "allFieldTypes" in customizationContext &&
        customizationContext.allFieldTypes
      ) {
        const category =
          customType.category === "collections" ? "collections" : "simple";
        const categoryData = customizationContext.allFieldTypes[category];

        if (categoryData?.fields?.[customType.key]) {
          fieldData = categoryData.fields[customType.key];
        }
      }

      // If we couldn't get data from context, create fallback data
      if (!fieldData) {
        const schemaType =
          customType.key === "array"
            ? "array"
            : customType.key === "object"
              ? "object"
              : customType.key === "number"
                ? "number"
                : "string";

        fieldData = {
          title: customType.title,
          icon: <span>{customType.title.charAt(0)}</span>, // Fallback icon
          description: customType.description,
          child: {},
          default: {
            schema: {
              type: schemaType,
              ...(schemaType === "object" ? { properties: {} } : {}),
              ...(schemaType === "array" ? { items: {} } : {}),
            },
            uiSchema: customType.key === "text" ? { "ui:widget": "text" } : {},
          },
        };
      }

      result.push({
        ...customType,
        data: fieldData,
      });
    }

    return result;
  }, [customizationContext]);

  return (
    <div className="grid gap-3">
      {fieldTypes.map((fieldType) => (
        <DraggableFieldCard key={fieldType.key} fieldType={fieldType} />
      ))}
    </div>
  );
};

export default function FieldTypePicker() {
  return (
    <DndProvider backend={MultiBackend} options={HTML5toTouch} context={window}>
      <FieldTypePickerContent />
    </DndProvider>
  );
}
