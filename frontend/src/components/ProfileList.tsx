import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import type { Profile } from '../types';

interface Props {
  profiles: Profile[];
  selectedId?: string;
  onSelect: (profile: Profile) => void;
}

export function ProfileList({ profiles, selectedId, onSelect }: Props) {
  if (profiles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8">
        <div className="text-4xl mb-3">📋</div>
        <div className="text-sm text-center">No hay perfiles aún.<br />Aparecerán aquí cuando el bot complete una conversación.</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {profiles.map((profile) => (
        <ProfileItem
          key={profile.id}
          profile={profile}
          isSelected={profile.id === selectedId}
          onClick={() => onSelect(profile)}
        />
      ))}
    </div>
  );
}

interface ItemProps {
  profile: Profile;
  isSelected: boolean;
  onClick: () => void;
}

function ProfileItem({ profile, isSelected, onClick }: ItemProps) {
  const timeAgo = formatDistanceToNow(new Date(profile.created_at), {
    addSuffix: true,
    locale: es,
  });

  const initials = (profile.instagram_username ?? 'U').slice(0, 2).toUpperCase();

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors border-b border-gray-100 ${
        isSelected ? 'bg-blue-50 border-l-2 border-l-blue-600' : ''
      }`}
    >
      <div className="flex-shrink-0">
        {profile.profile_pic_url ? (
          <img
            src={profile.profile_pic_url}
            alt={profile.instagram_username ?? ''}
            className="w-12 h-12 rounded-full object-cover"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-400 to-teal-400 flex items-center justify-center text-white font-semibold text-sm">
            {initials}
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-gray-900 text-sm truncate">
            {profile.instagram_username ?? 'Usuario desconocido'}
          </span>
          <span className="text-xs text-gray-400 flex-shrink-0">{timeAgo}</span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-snug">
          {profile.summary}
        </p>
      </div>
    </button>
  );
}
