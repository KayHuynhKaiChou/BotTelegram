const queryClient = useQueryClient();

const createPost = async (newPost) => {
  const { data } = await axios.post("/api/posts", newPost);
  return data;
};

// o submitform khi dung mutation.mutate(newPostPayload) thì newPostPayload chinh la newPost của onMutate và mutationFn

const mutation = useMutation({
    // flow : onMutate -> mutationFn -> onError(if call API fail) -> onSettled
  mutationFn: createPost,
  onMutate: async (newPost) => {
    // Hủy query cũ để tránh xung đột
    await queryClient.cancelQueries({ queryKey: ["posts"] });

    // Lấy snapshot trước khi update
    const previousPosts = queryClient.getQueryData(["posts"]);

    // update list posts tạm thời ở FE để UI show nhanh hơn
    queryClient.setQueryData(["posts"], (old: any) => [
      ...old,
      { id: Date.now(), ...newPost },
    ]);
    return { previousPosts };
  },
  onError: (_err, _newPost, context) => {
    // quay lại list posts trước đó (trước khi add new post)
    queryClient.setQueryData(["posts"], context?.previousPosts);
  },
  onSettled: () => {
    // chạy DÙ THÀNH CÔNG HAY LỖI
    // list posts từ server sẽ thay cho list posts tạm thời đc xử lí từ FE ở onMutate
    // hay nói cách khác là đồng bộ data cache với data server
    queryClient.invalidateQueries({ queryKey: ["posts"] });
  },
});
