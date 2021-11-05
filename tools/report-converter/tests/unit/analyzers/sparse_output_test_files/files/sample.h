static inline struct task_struct *get_task_struct(struct task_struct *t1, struct task_struct *t2)
{
	refcount_inc(t1, t2);
	return t2;
}

void refcount_inc(struct task_struct *t1, struct task_struct *t2)
{
	return;
}
