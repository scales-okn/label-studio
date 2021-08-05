import React, {} from 'react';
import { LsPlus } from '../../assets/icons';
import { Button } from '../../components';
import { Form, Label, Input } from '../../components/Form';
import { modal } from '../../components/Modal/Modal';
import { Elem, Block } from '../../utils/bem';
import "./WebhookPage.styl";


const WebhookList = ({ onSelectActive, onAddWebhook, webhooks }) => {
  if (webhooks === null) return <></>;

  return <Block name='webhook'>
    <Elem name='controls'>
      <Button onClick={onAddWebhook}>
        Add Webhook
      </Button>
    </Elem>
    <Elem name='content'>
      {webhooks.length === 0? 
        <p>Add new webhooks here.</p> 
        :
        <Block name='webhook-list'>
          {
            webhooks.map(
              (obj) => <Elem key={obj.id} name='item' onClick={() => onSelectActive(obj.id)}>
                <Elem tag='span' name='item-status' mod={{ active: obj.is_active }}>
                </Elem>
                <Elem name='item-url'>
                  {obj.url}
                </Elem>
                <Elem name='item-type'>
                  {obj.send_for_all}
                </Elem>
              </Elem>,
            )
          }
        </Block>}
    </Elem>
  </Block>;
};


export default WebhookList;
