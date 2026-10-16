import { queryOptions } from '@tanstack/react-query'

import { client, unwrap, uploadFiles } from '@/shared/api'

export const profileQuery = queryOptions({
  queryKey: ['profile'],
  queryFn: () => unwrap(client.GET('/api/profile')),
})

export async function setAvatar(file: File) {
  const [uploaded] = await uploadFiles([file], (body) => unwrap(client.POST('/api/profile/avatar/uploads', { body })))
  return unwrap(client.PUT('/api/profile/avatar', { body: { key: uploaded.key } }))
}

export const removeAvatar = () => unwrap(client.DELETE('/api/profile/avatar'))
