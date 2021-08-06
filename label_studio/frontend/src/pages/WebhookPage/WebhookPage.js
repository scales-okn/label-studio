import React, { useState, useCallback, useEffect } from 'react';

import { useAPI } from '../../providers/ApiProvider';
import "./WebhookPage.styl";


import WebhookList from './WebhookList';
import WebhookDetail from './WebhookDetail';
import { useProject } from '../../providers/ProjectProvider';
import { Spinner } from '../../components';

const Webhook = () => {
  const [activeWebhook, setActiveWebhook] = useState(null);
  const [webhooks, setWebhooks] = useState(null);
  const [webhooksInfo, setWebhooksInfo] = useState(null);
  
  
  const api = useAPI();
  const { project } = useProject();
  
  const [projectId, setProjectId] = useState(project.id);

  useEffect(()=>{
    if (Object.keys(project).length === 0) {
      setProjectId(null);
    }else{
      setProjectId(project.id);
    }

  }, [project]);


  const fetchWebhooks = useCallback(async () => {
    if (projectId === undefined) {
      setWebhooks(null);
      return;
    }
    const webhooks = await api.callApi('webhooks', {
      params: {
        project: projectId,
      },
    });
    if (webhooks) setWebhooks(webhooks);
  }, [api, projectId]);

  const fetchWebhooksInfo = useCallback(async () => {
    const info = await api.callApi('webhooksInfo');
    if (info) setWebhooksInfo(info);
  }, [api, projectId]);

  useEffect(() => {
    fetchWebhooks();
    fetchWebhooksInfo();
  }, [api, project, projectId]);

  if (webhooks === null || webhooksInfo === null || projectId === undefined) {
    return null;
  }
  if (activeWebhook==='new') {
    return <WebhookDetail
      onSelectActive={setActiveWebhook}
      onBack={() => setActiveWebhook(null)}
      webhook={null}
      fetchWebhooks={fetchWebhooks}
      webhooksInfo={webhooksInfo} />;  
  } else if (activeWebhook === null) {
    return <WebhookList
      onSelectActive={setActiveWebhook}
      onAddWebhook={()=>{setActiveWebhook('new');}}
      fetchWebhooks={fetchWebhooks}
      webhooks={webhooks}       
    />;
  } else {
    return <WebhookDetail
      onSelectActive={setActiveWebhook}
      onBack={() => setActiveWebhook(null)}
      webhook={webhooks[webhooks.findIndex((x) => x.id === activeWebhook)]}
      fetchWebhooks={fetchWebhooks}
      webhooksInfo={webhooksInfo} />;
  }
};

export const WebhookPage = {
  title: "Webhooks",
  path: "/webhooks",
  component: Webhook,
};