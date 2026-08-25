import { ImagePlus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import type { User } from "../types/api";
import { UserAvatar } from "./UserAvatar";

interface ProfileImagePickerProps {
  fullName: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
  user?: Pick<User, "id" | "full_name" | "has_avatar" | "avatar_updated_at">;
  onRemove?: () => void;
  removing?: boolean;
}

export function ProfileImagePicker({
  fullName,
  file,
  onFileChange,
  user,
  onRemove,
  removing = false,
}: ProfileImagePickerProps) {
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return (
    <div className="profile-image-picker">
      {previewUrl ? (
        <span className="avatar avatar-with-image avatar-preview">
          <img src={previewUrl} alt="Pré-visualização da foto" />
        </span>
      ) : user ? (
        <UserAvatar
          userId={user.id}
          fullName={user.full_name}
          hasAvatar={user.has_avatar}
          avatarUpdatedAt={user.avatar_updated_at}
          className="avatar-preview"
        />
      ) : (
        <span className="avatar avatar-preview">{fullName.slice(0, 1).toUpperCase() || "?"}</span>
      )}
      <div className="profile-image-actions">
        <label className="button secondary avatar-file-button">
          <ImagePlus size={15} /> {file ? "Trocar arquivo" : "Escolher foto"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            aria-label="Foto do usuário"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          />
        </label>
        {file && (
          <button className="button ghost" type="button" onClick={() => onFileChange(null)}>
            Cancelar foto
          </button>
        )}
        {!file && user?.has_avatar && onRemove && (
          <button className="button ghost" type="button" disabled={removing} onClick={onRemove}>
            <Trash2 size={14} /> {removing ? "Removendo…" : "Remover foto"}
          </button>
        )}
        <small>JPG, PNG ou WebP. A imagem será otimizada com segurança.</small>
      </div>
    </div>
  );
}
