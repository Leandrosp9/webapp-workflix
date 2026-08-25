import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getBlob } from "../services/http";

interface UserAvatarProps {
  userId: string;
  fullName: string;
  hasAvatar?: boolean;
  avatarUpdatedAt?: string | null;
  className?: string;
}

export function UserAvatar({
  userId,
  fullName,
  hasAvatar = false,
  avatarUpdatedAt,
  className = "",
}: UserAvatarProps) {
  const [imageUrl, setImageUrl] = useState("");
  const query = useQuery({
    queryKey: ["user-avatar", userId, avatarUpdatedAt],
    queryFn: () =>
      getBlob(
        `/users/${userId}/avatar${avatarUpdatedAt ? `?v=${encodeURIComponent(avatarUpdatedAt)}` : ""}`,
      ),
    enabled: hasAvatar,
    staleTime: Number.POSITIVE_INFINITY,
    retry: false,
  });

  useEffect(() => {
    if (!query.data) {
      setImageUrl("");
      return;
    }
    const url = URL.createObjectURL(query.data);
    setImageUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [query.data]);

  return (
    <span className={`avatar ${imageUrl ? "avatar-with-image" : ""} ${className}`.trim()}>
      {imageUrl ? (
        <img src={imageUrl} alt={`Foto de ${fullName}`} />
      ) : (
        fullName.slice(0, 1).toUpperCase()
      )}
    </span>
  );
}
