import {getFormattedMessage} from 'app/util/messageUtil';
import {
    addErrorMsg,
    removeWarningMsg,
    addClickListener
} from 'app/util/promptMsgController';

define([
    'jquery',
    'lodash',
    'backbone',
    'app/views/component/DeleteDialog.html'
], function (
    $,
    _,
    Backbone,
    DeleteDialog
) {
    return Backbone.View.extend({
        events: {
            "submit form": "delete"
        },

        initialize: function (options) {
            this.collection = options.collection;
            this.model = options.model;
            this.stateModel = options.stateModel;
            this.dispatcher = options.dispatcher;
            this.inUse = options.inUse;
            this.deleteTag = options.deleteTag;
        },

        render: function () {
            this.$el.html(_.template(DeleteDialog)({
                title: getFormattedMessage(101),
                inUse: this.inUse,
                inUseMsg: getFormattedMessage(
                    102,
                    this.model.entry.attributes.name
                ),
                notinUseMsg: getFormattedMessage(
                    103,
                    this.model.entry.attributes.name,
                    this.deleteTag || ''
                 )
            }));

            var dlg = this;
            this.$("[role=dialog]").on('hidden.bs.modal', function () {
                dlg.undelegateEvents();
            });
            return this;
        },

        delete: function () {
            var url, collection, delete_url, self;
            collection = this.model.collection;
            if (!collection) {
                collection = this.collection;
            }
            url =  this.model._url === undefined ? collection._url : this.model._url;
            delete_url = [
                collection.proxyUrl,
                url,
                this.encodeUrl(this.model.entry.attributes.name)
            ].join("/") + '?output_mode=json';

            this._delete(delete_url);
        },

        modal: function () {
            this.$("[role=dialog]").modal({backdrop: 'static', keyboard: false});
        },

        encodeUrl: function (str) {
            return encodeURIComponent(str).replace(/'/g, "%27").replace(/"/g, "%22");
        },

        _delete: function (delete_url) {
            this.$("input[type=submit]").attr('disabled', true);
            $.ajax({
                url: delete_url,
                type: 'DELETE'
            }).done(() => {
                this.collection.remove(this.model);

                if (this.collection.length > 0) {
                    _.each(this.collection.models, (model) => {
                        model.paging.set('total', model.paging.get('total') - 1);
                    });
                    this.collection.reset(this.collection.models);
                    //Trigger collection page change event to refresh the count in table caption
                    this.collection.paging.set('total', this.collection.models.length);
                } else {
                    var offset = this.stateModel.get('offset'),
                        count = this.stateModel.get('count');
                    this.collection.paging.set('offset', (offset - count) < 0 ? 0 : (offset - count));
                    this.collection.paging.set('perPage', count);
                    this.collection.paging.set('total', offset);

                    _.each(this.collection.models, (model) => {
                        model.paging.set('offset', (offset - count) < 0 ? 0 : (offset - count));
                        model.paging.set('perPage', count);
                        model.paging.set('total', offset);
                    });

                    this.stateModel.set('offset', (offset - count) < 0 ? 0 : (offset - count));
                    this.collection.reset(null);
                }

                if (this.collection._url === undefined) {
                    this.dispatcher.trigger('delete-input');
                }
                this.$("[role=dialog]").modal('hide');
            }).fail((model, response) => {
                //Re-enable when failed
                this.$("input[type=submit]").removeAttr('disabled');
                removeWarningMsg('.modal-dialog');
                addErrorMsg('.modal-dialog', model, true);
                addClickListener('.modal-dialog', 'msg-error');
            });
        }
    });
});
