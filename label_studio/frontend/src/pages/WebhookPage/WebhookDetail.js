
import React, { useState, useEffect} from 'react';
import { Button } from '../../components';
import { Form, Label, Input, Toggle } from '../../components/Form';
import { Elem, Block, cn } from '../../utils/bem';
import { cloneDeep } from 'lodash';
import { LsCross, LsPlus } from '../../assets/icons';
import { useAPI } from '../../providers/ApiProvider';
import "./WebhookPage.styl";
import { Space } from '../../components/Space/Space';
import { useProject } from '../../providers/ProjectProvider';


const WebhookDetail = ({ webhook, webhooksInfo, fetchWebhooks, onBack }) => {

  // if webhook === null - create mod
  // else update
  const rootClass = cn('webhook-detail');

  const api = useAPI(); 
  const {project} = useProject();
  const [headers, setHeaders] = useState([]);
  const [sendForAllActions, setSendForAllActions] = useState(true);
  const [actions, setActions] = useState(new Set());

  const onAddHeaderClick = () => {
    if (!(headers.find(([k]) => k === ''))) {
      setHeaders([...headers, ['', '']]);
    }
  };
  const onHeaderRemove = (index) => {
    let newHeaders = cloneDeep(headers);
    newHeaders.splice(index, 1);
    setHeaders(newHeaders);
  };
  const onHeaderChange = (aim, event, index) => {
    let newHeaders = cloneDeep(headers);
    if (aim === 'key') {
      newHeaders[index][0] = event.target.value;
    }
    if (aim === 'value') {
      newHeaders[index][1] = event.target.value;
    }
    setHeaders(newHeaders);
  };

  const onActionChange = (event) => {
    let newActions = new Set(actions);
    if (event.target.checked) {
      newActions.add(event.target.name);
    } else {
      newActions.delete(event.target.name);
    }
    setActions(newActions);
  };

  useEffect(() => {
    if (webhook === null) {
      setHeaders([]);
      setSendForAllActions(true);
      setActions(new Set());
      return;
    }
    setHeaders(Object.entries(webhook.headers));
    setSendForAllActions(webhook.send_for_all_actions);
    setActions(new Set(webhook.actions));
  }, [webhook]);

  // if (webhook === null || headers === null || sendForAllActions === null) return <></>;
  return <Block name='webhook'>
    <Elem name='title'>
      <><Elem tag='span' name='title-base'>Webhooks</Elem>  /  {webhook===null? 'New Webhook' : 'Edit Webhook'}</>
    </Elem>
    <Elem name='content'>
      <Block name={'webhook-detail'}>
        <Form
          action={webhook===null ? 'createWebhook' :  'updateWebhook'}
          params={webhook===null ? {} : { pk: webhook.id }}
          formData={webhook}
          prepareData={(data) => {
            return {
              ...data,
              'send_for_all_actions': sendForAllActions,
              'headers': Object.fromEntries(headers),
              'actions': Array.from(actions),
            };
          }}
          onSubmit={async (response) => {
            if (!response.error_message) {
              await fetchWebhooks();
            }
          }}
        >
          <Form.Row style={{marginBottom: '40px'}} columnCount={1}>
            <Label text='Payload URL' style={{marginLeft: '-16px'}} large></Label>
            <Space className={rootClass.elem('url-space')}>
              <Input name="url" className={rootClass.elem('url-input')} placeholder="URL" />
              <Space align='end' className={rootClass.elem('activator')}>
                <span className={rootClass.elem('black-text')}>Is Active</span>
                <Toggle name="is_active" />
              </Space>
            </Space>
          </Form.Row>
          <Form.Row style={{marginBottom: '40px'}} columnCount={1}>
            <div className={rootClass.elem('headers')}>
              <div className={rootClass.elem('headers-content')}>
                <Space spread className={rootClass.elem('headers-control')}>
                  <Label text="Headers" large />
                  <Button disabled={headers.find(([k]) => k === '')} type='button' onClick={onAddHeaderClick} 
                    className={rootClass.elem('headers-add')}
                    icon={<LsPlus />}
                  />
                </ Space>
                {
                  headers.map(([headKey, headValue], index) => {
                    return <Space key={index} className={rootClass.elem('headers-row')} columnCount={3} >
                      <Input className={rootClass.elem('headers-input')} 
                        skip 
                        placeholder="header" 
                        value={headKey} 
                        onChange={(e) => onHeaderChange('key', e, index)} />
                      <Input className={rootClass.elem('headers-input')} 
                        skip 
                        placeholder="value"
                        value={headValue} 
                        onChange={(e) => onHeaderChange('value', e, index)} />
                      <div>
                        <Button className={rootClass.elem('headers-remove')} 
                          type='button' 
                          icon={<LsCross />} 
                          onClick={() => onHeaderRemove(index)}></Button>
                      </div>
                    </Space>;
                  })
                }
              </div>
            </div>
          </Form.Row>
          <Block name='webhook-payload' style={{marginBottom: '40px'}} columnCount={1}>
            <Elem name='title'>
              <Label text="Payload" large />
            </Elem>
            <Elem name='content'>
              <Elem name='content-row'>
                <Toggle name="send_payload" label="Send payload"></Toggle>
              </Elem>
              <Elem name='content-row'>
                <Toggle skip checked={sendForAllActions} label="Send for all actions" onChange={(e) => { setSendForAllActions(e.target.checked); }} />
              </Elem>
              <div >
                {
                  !sendForAllActions ?
                    <Elem name='content-row-actions'>
                      <Elem tag='h4' name='title' mod={{black:true}}>
                        Send Payload for
                      </Elem>
                      <Elem name='actions'>
                        {Object.entries(webhooksInfo).map(([key, value]) => {
                          return <Form.Row key={key} columnCount={1}>
                            <div>
                              <Toggle skip name={key} type='checkbox' label={value.name} onChange={onActionChange} checked={actions.has(key)}></Toggle>
                            </div>
                          </Form.Row>;
                        })}
                      </Elem>
                    </Elem>
                    :
                    null
                }
              </div>
            </Elem>
          </Block>
          <Elem name='controls'>
            <Button 
              look="danger"
              type='button'
              className={rootClass.elem('delete-button')}
              onClick={async ()=>{
                await api.callApi('deleteWebhook', {params:{pk:webhook.id}});
                onBack();
                await fetchWebhooks();
              }}>
                Delete Webhook...
            </Button>
            <Button 
              type='button'
              className={rootClass.elem('cancel-button')}
              onClick={onBack}
            >Cancel
            </Button>
            <Button 
              primary
              className={rootClass.elem('save-button')}
            >
              Save
            </Button>
          </Elem>
        </Form>
      </Block>

    </Elem>
  </Block >;
};

export default WebhookDetail;