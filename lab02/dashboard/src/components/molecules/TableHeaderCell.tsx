import React from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

interface TableHeaderCellProps<T extends string> {
  field: T;
  currentSortField: T;
  sortDirection: 'asc' | 'desc';
  onSort: (field: T) => void;
  children: React.ReactNode;
  className?: string;
}

export function TableHeaderCell<T extends string>({
  field,
  currentSortField,
  sortDirection,
  onSort,
  children,
  className = '',
}: TableHeaderCellProps<T>) {
  const isSorted = currentSortField === field;

  return (
    <th
      onClick={() => onSort(field)}
      className={`py-2.5 px-3 cursor-pointer select-none transition-colors hover:text-gray-900 dark:hover:text-white ${className}`}
    >
      <div className="flex items-center gap-1">
        <span>{children}</span>
        {isSorted ? (
          sortDirection === 'asc' ? (
            <ArrowUp className="w-3 h-3 text-blue-500 shrink-0" />
          ) : (
            <ArrowDown className="w-3 h-3 text-blue-500 shrink-0" />
          )
        ) : (
          <ArrowUpDown className="w-3 h-3 text-gray-400 opacity-60 shrink-0" />
        )}
      </div>
    </th>
  );
}
