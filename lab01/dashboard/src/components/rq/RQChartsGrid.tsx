import React from 'react';
import { RQStats } from '../../types/dataset';
import { RQ01AgeCard } from './RQ01AgeCard';
import { RQ02PRsCard } from './RQ02PRsCard';
import { RQ03ReleasesCard } from './RQ03ReleasesCard';
import { RQ04UpdateCard } from './RQ04UpdateCard';
import { RQ05LanguagesCard } from './RQ05LanguagesCard';
import { RQ06IssuesRatioCard } from './RQ06IssuesRatioCard';
import { RQ07LangComparisonCard } from './RQ07LangComparisonCard';

interface RQChartsGridProps {
  stats: RQStats | null;
}

export const RQChartsGrid: React.FC<RQChartsGridProps> = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="space-y-6">
      {/* 2-Column Grid for RQ01 to RQ06 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RQ01AgeCard stats={stats} />
        <RQ02PRsCard stats={stats} />
        <RQ03ReleasesCard stats={stats} />
        <RQ04UpdateCard stats={stats} />
        <RQ05LanguagesCard stats={stats} />
        <RQ06IssuesRatioCard stats={stats} />
      </div>

      {/* Full-Width Card for RQ07 */}
      <RQ07LangComparisonCard stats={stats} />
    </div>
  );
};
