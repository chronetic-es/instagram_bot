import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import type { Profile } from '../types';

interface Props {
  profile: Profile;
  onViewConversation: (conversationId: string) => void;
  onBack?: () => void;
}

export function ProfileDetail({ profile, onViewConversation, onBack }: Props) {
  const initials = (profile.instagram_username ?? 'U').slice(0, 2).toUpperCase();
  const createdAt = format(new Date(profile.created_at), "d 'de' MMMM yyyy, HH:mm", { locale: es });

  return (
    <div className="flex flex-col h-full overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200 flex-shrink-0">
        {onBack && (
          <button
            onClick={onBack}
            className="text-gray-500 hover:text-gray-700 mr-1 md:hidden"
            aria-label="Volver"
          >
            ←
          </button>
        )}
        <div className="flex-shrink-0">
          {profile.profile_pic_url ? (
            <img
              src={profile.profile_pic_url}
              alt={profile.instagram_username ?? ''}
              className="w-10 h-10 rounded-full object-cover"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-400 to-teal-400 flex items-center justify-center text-white font-semibold text-sm">
              {initials}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-900 text-sm truncate">
            {profile.instagram_username ?? 'Usuario desconocido'}
          </div>
          <div className="text-xs text-gray-400">{createdAt}</div>
        </div>
        <button
          onClick={() => onViewConversation(profile.conversation_id)}
          className="flex-shrink-0 text-xs text-blue-600 hover:text-blue-800 font-medium px-3 py-1.5 rounded-lg border border-blue-200 hover:bg-blue-50 transition-colors"
        >
          Ver conversación
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Summary */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            Resumen
          </div>
          <p className="text-sm text-gray-800 leading-relaxed">{profile.summary}</p>
        </div>

        {/* Q&A */}
        {profile.answers.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            <div className="px-4 py-3">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Respuestas ({profile.answers.length})
              </div>
            </div>
            {profile.answers.map((item, idx) => (
              <div key={idx} className="px-4 py-3">
                <div className="text-xs text-gray-400 mb-1">{item.question}</div>
                <div className="text-sm text-gray-800">{item.answer}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
