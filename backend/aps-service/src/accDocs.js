import { DataManagementClient } from '@aps_sdk/data-management';

export function createAccDocsApi({ getUserAuthHeader }) {
  const dm = new DataManagementClient();

  async function hubs() {
    return await dm.getHubs({ authorization: await getUserAuthHeader() });
  }

  async function projects(hubId) {
    return await dm.getHubProjects(hubId, { authorization: await getUserAuthHeader() });
  }

  async function topFolders(hubId, projectId) {
    return await dm.getProjectTopFolders(hubId, projectId, { authorization: await getUserAuthHeader() });
  }

  async function folderContents(projectId, folderId) {
    return await dm.getFolderContents(projectId, folderId, { authorization: await getUserAuthHeader() });
  }

  async function itemVersions(projectId, itemId) {
    return await dm.getItemVersions(projectId, itemId, { authorization: await getUserAuthHeader() });
  }

  async function versionDetails(projectId, versionId) {
    return await dm.getVersion(projectId, versionId, { authorization: await getUserAuthHeader() });
  }

  return {
    hubs,
    projects,
    topFolders,
    folderContents,
    itemVersions,
    versionDetails
  };
}
