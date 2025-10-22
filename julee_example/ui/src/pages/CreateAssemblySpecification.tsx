import AssemblySpecificationForm from "@/components/AssemblySpecificationForm";

export default function CreateAssemblySpecificationPage() {
  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Create Assembly Specification
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Define a new assembly specification that describes how to structure
          extracted data into documents like meeting minutes, reports, or
          summaries.
        </p>
      </div>

      <AssemblySpecificationForm />
    </div>
  );
}
