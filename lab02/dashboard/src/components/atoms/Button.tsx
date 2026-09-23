import React from 'react';

export type ButtonVariant = 'primary' | 'outline' | 'ghost' | 'icon';
export type ButtonSize = 'sm' | 'md';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'outline',
  size = 'sm',
  icon,
  children,
  className = '',
  disabled,
  ...props
}) => {
  const sizeClasses =
    variant === 'icon'
      ? 'p-1.5'
      : size === 'sm'
      ? 'px-2.5 py-1.5 text-xs'
      : 'px-3.5 py-2 text-sm';

  let variantClasses = '';
  switch (variant) {
    case 'primary':
      variantClasses =
        'bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-sm border border-transparent';
      break;
    case 'outline':
      variantClasses =
        'bg-white dark:bg-github-dark hover:bg-gray-100 dark:hover:bg-github-border/50 text-gray-700 dark:text-github-text border border-gray-200 dark:border-github-border font-medium';
      break;
    case 'ghost':
      variantClasses =
        'hover:bg-gray-100 dark:hover:bg-github-border/50 text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white';
      break;
    case 'icon':
      variantClasses =
        'hover:bg-gray-100 dark:hover:bg-github-card text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white rounded-lg';
      break;
  }

  const disabledClasses = disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer';

  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg transition-colors ${sizeClasses} ${variantClasses} ${disabledClasses} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
};
