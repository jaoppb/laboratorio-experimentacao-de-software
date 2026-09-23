import React from 'react';
import { User, Sparkles } from 'lucide-react';
import { Badge } from '../atoms/Badge';
import { UnifiedTrial } from '../../types/dataset';

interface TrialBadgesProps {
  trial: UnifiedTrial;
  className?: string;
}

export const TrialBadges: React.FC<TrialBadgesProps> = ({
  trial,
  className = '',
}) => {
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <span className="font-mono font-bold text-sm text-gray-900 dark:text-white">
        {trial.trial_id}
      </span>
      <Badge variant={trial.treatment === 'ai' ? 'primary' : 'warning'}>
        {trial.treatment === 'ai' ? 'Tratamento: Com IA' : 'Tratamento: Manual'}
      </Badge>
      {trial.ai_model && (
        <Badge variant="purple" icon={<Sparkles className="w-3 h-3" />}>
          {trial.ai_model}
        </Badge>
      )}
      <Badge variant="neutral" icon={<User className="w-3 h-3" />}>
        {trial.participant}
      </Badge>
      <Badge variant="neutral">{trial.kata_title}</Badge>
    </div>
  );
};
