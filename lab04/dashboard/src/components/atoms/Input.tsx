import React from 'react';

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value: string;
  onChange: (value: string) => void;
  icon?: React.ReactNode;
  className?: string;
}

export const Input: React.FC<InputProps> = ({
  value,
  onChange,
  icon,
  className = '',
  ...props
}) => {
  return (
    <div className="relative w-full">
      {icon && (
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
          {icon}
        </span>
      )}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full text-xs bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-lg ${
          icon ? 'pl-8' : 'pl-2.5'
        } pr-2.5 py-2 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors ${className}`}
        {...props}
      />
    </div>
  );
};
