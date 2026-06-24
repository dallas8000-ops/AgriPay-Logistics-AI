import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  badge?: string;
}

export default function PageHeader({ title, subtitle, action, badge }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        {badge && <span className="page-header-badge">{badge}</span>}
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {action && <div className="page-header-action">{action}</div>}
    </header>
  );
}
