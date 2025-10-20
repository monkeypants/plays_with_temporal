export default function QueriesPage() {
  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Knowledge Service Queries
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Manage and monitor your knowledge service queries
        </p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-primary-100 dark:bg-primary-900">
            <svg
              className="h-6 w-6 text-primary-600 dark:text-primary-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
            Queries Management
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            This page will show all knowledge service queries, their status, and allow you to create new ones.
          </p>
          <div className="mt-6">
            <button
              type="button"
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <svg
                className="-ml-1 mr-2 h-5 w-5"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clipRule="evenodd"
                />
              </svg>
              Create New Query
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
