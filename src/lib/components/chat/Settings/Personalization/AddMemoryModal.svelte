<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { addExternalMemory } from '$lib/apis/soren_memories';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let show;
	const i18n = getContext('i18n');

	let loading = false;
	let content = '';
	let importance: number = 5;
	let tagsText: string = '';
	let metadataText: string = '';

	const submitHandler = async () => {
		loading = true;

		let tags: string[] = tagsText
			.split(',')
			.map((t) => t.trim())
			.filter((t) => t.length > 0);
		let metadata: any = undefined;
		if (metadataText && metadataText.trim().length > 0) {
			try {
				metadata = JSON.parse(metadataText);
			} catch (e) {
				toast.error($i18n.t('Invalid JSON in metadata'));
				loading = false;
				return;
			}
		}

		const res = await addExternalMemory(localStorage.token, content, importance, tags, metadata).catch((error) => {
			toast.error(`${error}`);

			return null;
		});

		if (res) {
			console.log(res);
			toast.success($i18n.t('Memory added successfully'));
			content = '';
			importance = 5;
			tagsText = '';
			metadataText = '';
			show = false;
			dispatch('save');
		}

		loading = false;
	};
</script>

<Modal bind:show size="sm">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">
				{$i18n.t('Add Memory')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="space-y-3">
						<div>
							<label class="block mb-1 text-xs text-gray-500">{$i18n.t('Content')}</label>
							<textarea
								bind:value={content}
								class=" bg-transparent w-full text-sm rounded-xl p-3 outline outline-1 outline-gray-100 dark:outline-gray-800"
								rows="5"
								style="resize: vertical;"
								placeholder={$i18n.t('Enter a detail for memory storage')}
							/>
						</div>

						<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
							<div>
								<label class="block mb-1 text-xs text-gray-500">{$i18n.t('Importance (1-10)')}</label>
								<input type="number" min="1" max="10" bind:value={importance}
									class=" bg-transparent w-full text-sm rounded-xl p-2 outline outline-1 outline-gray-100 dark:outline-gray-800" />
							</div>
							<div>
								<label class="block mb-1 text-xs text-gray-500">{$i18n.t('Tags (comma-separated)')}</label>
								<input type="text" bind:value={tagsText}
									class=" bg-transparent w-full text-sm rounded-xl p-2 outline outline-1 outline-gray-100 dark:outline-gray-800" />
							</div>
						</div>

						<div>
							<label class="block mb-1 text-xs text-gray-500">{$i18n.t('Metadata (JSON)')}</label>
                        <textarea bind:value={metadataText}
                            class=" bg-transparent w-full text-sm rounded-xl p-2 outline outline-1 outline-gray-100 dark:outline-gray-800"
                            rows="4"
                            style="resize: vertical;"
                            placeholder={`{"source":"user","category":"general"}`} />
						</div>
					</div>

					<div class="flex justify-end pt-1 text-sm font-medium">
						<button
							class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-3xl flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Add')}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
