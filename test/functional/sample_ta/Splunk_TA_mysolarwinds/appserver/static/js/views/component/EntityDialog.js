import {configManager} from 'app/util/configManager';
import restEndpointMap from 'app/constants/restEndpointMap';
import {generateModel, generateCollection} from 'app/util/backboneHelpers';
import {generateValidators} from 'app/util/validators';
import {parseFuncRawStr} from 'app/util/script';
import {
    addErrorMsg,
    removeErrorMsg,
    addSavingMsg,
    removeSavingMsg,
    displayValidationError,
    addClickListener
} from 'app/util/promptMsgController';
import {getFormattedMessage} from 'app/util/messageUtil';

define([
    'jquery',
    'lodash',
    'backbone',
    'app/util/Util',
    'app/models/Base.Model',
    'app/templates/common/AddDialog.html',
    'app/templates/common/EditDialog.html',
    'app/templates/common/CloneDialog.html',
    'app/templates/common/TabTemplate.html',
    'app/views/controls/ControlWrapper'
], function (
    $,
    _,
    Backbone,
    Util,
    BaseModel,
    AddDialogTemplate,
    EditDialogTemplate,
    CloneDialogTemplate,
    TabTemplate,
    ControlWrapper
) {
    return Backbone.View.extend({
        initialize: function (options) {
            this.unifiedConfig = configManager.unifiedConfig;
            this.appData = configManager.getAppData();
            _.extend(this, options);

            //guid of current dialog
            this.curWinId = Util.guid();
            this.curWinSelector = '.' + this.curWinId;
            //Encrypted field list
            this.encryptedFields = [];
            _.each(this.component.entity, e => {
                if (e.encrypted) {
                    this.encryptedFields.push(e.field);
                }
            });

            //Delete encrypted field in delete or clone mode
            if (options.model && this.encryptedFields.length) {
                _.each(this.encryptedFields, f => {
                    delete options.model.entry.content.attributes[f];
                });
            }

            this.model = new Backbone.Model({});

            const {entity, name, options: comOpt} = this.component;
            const validators = generateValidators(entity);
            const endpointUrl = restEndpointMap[name];
            const InputType = generateModel(endpointUrl ? '' : this.component.name, {
                modelName: name,
                fields: entity,
                endpointUrl,
                formDataValidatorRawStr: comOpt ? comOpt.saveValidator : undefined,
                onLoadRawStr: comOpt ? comOpt.onLoad : undefined,
                validators
            });

            if (!options.model) { //Create mode
                this.mode = "create";
                this.model = new Backbone.Model({});
                this.real_model = new InputType(null, {
                    appData: this.appData,
                    collection: this.collection
                });
            } else if (this.mode === "edit") { //Edit mode
                this.model = options.model.entry.content.clone();
                this.model.set({name: options.model.entry.get("name")});
                this.real_model = options.model;
            } else if (this.mode === "clone") { //Clone mode
                this.model = options.model.entry.content.clone();
                //Unset the name attribute if the model is newly created
                if (this.model.get("name")) {
                    this.model.unset("name");
                }
                //Unset the refCount attribute
                if (this.model.get("refCount")) {
                    this.model.unset("refCount");
                }
                this.cloneName = options.model.entry.get("name");
                this.real_model = new InputType(null, {
                    appData: this.appData,
                    collection: this.collection
                });
            }
            this.real_model.on("invalid", err => {
                displayValidationError(this.curWinSelector,  err);
                addClickListener(this.curWinSelector, 'msg-error');
            });

            // We can't set onChange-hook up in the data fetching model. Since it will only be updated when user save form data.
            this.model.on('change', this.onStateChange.bind(this));
            this.initModel();
        },

        onStateChange: function() {
            const onChangeHookRawStr = _.get(this.component, ['options', 'onChange']);
            if (onChangeHookRawStr) {
                const changedField = this.model.changedAttributes();
                const widgetsIdDict = {};
                const {entity, name} = this.component;
                (entity || []).forEach(d => {
                    widgetsIdDict[d.field] = `#${name}-${d.field}`;
                });
                const formData = this.model.toJSON();
                const onChangeHook = parseFuncRawStr(onChangeHookRawStr);
                onChangeHook(formData, changedField, widgetsIdDict);
            }
        },

        modal: function () {
            this.$("[role=dialog]").modal({backdrop: 'static', keyboard: false});
        },

        submitTask: function () {
            //Disable the button to prevent repeat submit
            this.$("input[type=submit]").attr('disabled', true);
            // Remove loading and error message
            removeErrorMsg(this.curWinSelector);
            removeSavingMsg(this.curWinSelector);
            //Save the model
            this.saveModel();
        },

        initModel: function() {
            const {content} = this.real_model.entry,
                {entity} = this.component;

            entity.forEach(d => {
                if (content.get(d.field) === undefined && d.defaultValue) {
                    content.set(d.field, d.defaultValue);
                }
            });
        },

        saveModel: function () {
            var input = this.real_model,
                new_json = this.model.toJSON(),
                original_json = input.entry.content.toJSON(),
                //Add label attribute for validation prompt
                entity = this.component.entity,
                attr_labels = {};
            _.each(entity, function (e) {
                attr_labels[e.field] = e.label;
            });

            input.entry.content.set(new_json);
            input.attr_labels = attr_labels;

            return this.save(input, original_json);
        },

        save: function (input, original_json) {
            var deffer = input.save();

            if (!deffer.done) {
                input.entry.content.set(original_json);
                input.trigger('change');
                //Re-enable when failed
                this.$("input[type=submit]").removeAttr('disabled');
            } else {
                addSavingMsg(this.curWinSelector, getFormattedMessage(108));
                addClickListener(this.curWinSelector, 'msg-loading');
                deffer.done(() => {
                    //Delete encrypted field before adding to collection
                    if (this.encryptedFields.length) {
                        _.each(this.encryptedFields, f => {
                            delete input.entry.content.attributes[f];
                        });
                    }
                    this.collection.trigger('change');

                    //Add model to collection
                    if (this.mode !== 'edit') {
                        this.collection.add(input);
                        if (this.collection.length !== 0) {
                            _.each(this.collection.models, (model) => {
                                model.paging.set('total', this.collection.length);
                            });
                        }

                        //Trigger collection page change event to refresh the count in table caption
                        this.collection.paging.set('total', this.collection.models.length);
                        //Rerender the table
                        this.collection.reset(this.collection.models);

                        //trigger type change event
                        // TODO: Change me
                        //if (this.dispatcher) {
                        //this.dispatcher.trigger('filter-change',this.service_type);
                        //}
                    }
                    this.$("[role=dialog]").modal('hide');
                    this.undelegateEvents();
                }).fail((model, response) => {
                    console.log("error happended.");
                    input.entry.content.set(original_json);
                    input.trigger('change');
                    // re-enable when failed
                    this.$("input[type=submit]").removeAttr('disabled');
                    removeSavingMsg(this.curWinSelector);
                    addErrorMsg(this.curWinSelector, model, true);
                    addClickListener(this.curWinSelector, 'msg-error');
                });
            }
            return deffer;
        },

        render: function () {
            var templateMap = {
                    "create": AddDialogTemplate,
                    "edit": EditDialogTemplate,
                    "clone": CloneDialogTemplate
                },
                template = _.template(templateMap[this.mode]),
                jsonData = this.mode === "clone" ? {
                    name: this.cloneName,
                    title: this.component.title
                } : {
                    title: this.component.title,
                    isInput: this.isInput
                },
                entity = this.component.entity;

            this.$el.html(template(jsonData));

            this.$("[role=dialog]").on('hidden.bs.modal', () => {
                this.undelegateEvents();
            });

            this.children = [];
            _.each(entity, (e) => {
                var option, controlWrapper, controlOptions;
                if (this.model.get(e.field) === undefined && e.defaultValue) {
                    this.model.set(e.field, e.defaultValue);
                }

                controlOptions = {
                    model: this.model,
                    modelAttribute: e.field,
                    password: e.encrypted ? true : false,
                    displayText: e.displayText,
                    helpLink: e.helpLink,
                    elementId: `${this.component.name}-${e.field}`
                };
                _.extend(controlOptions, e.options);

                controlWrapper = new ControlWrapper({...e, controlOptions});

                if (e.display !== undefined) {
                    controlWrapper.$el.css("display", "none");
                }
                this.children.push(controlWrapper);
            });

            _.each(this.children, (child) => {
                // prevent auto complete for password
                if (child.controlOptions.password) {
                    this.$('.modal-body').prepend(
                        `<input type="password" id="${child.controlOptions.modelAttribute}" style="display: none"/>`
                    );
                }
                this.$('.modal-body').append(child.render().$el);
            });

            //Disable the name field in edit mode
            if (this.mode === 'edit') {
                this.$("input[name=name]").attr("readonly", "readonly");
            }
            this.$("input[type=submit]").on("click", this.submitTask.bind(this));
            //Add guid to current dialog
            this.$(".modal-dialog").addClass(this.curWinId);

            return this;
        },

        // TODO: delete this method after we fix the missing "default" in index selector.
        _loadIndex: function (controlWrapper) {
            const indexes = generateCollection('indexes');
            const indexDeferred = indexes.fetch();
            indexDeferred.done(() => {
                let id_lst = _.map(indexes.models, model => {
                    return {
                        label: model.entry.attributes.name,
                        value: model.entry.attributes.name
                    };
                });

                //Ensure the model's index value in list
                id_lst = this._ensureIndexInList(id_lst);

                if (_.find(id_lst, function (item) {
                        return item.value === "default";
                    }) === undefined) {
                    id_lst = id_lst.concat({
                        label: "default",
                        value: "default"
                    });
                }
                controlWrapper.control.setAutoCompleteFields(id_lst, true);
            }).fail(() => {
                addErrorMsg(this.curWinSelector, getFormattedMessage(109));
            });
        },

        _ensureIndexInList: function (data) {
            var selected_value = this.model.get('index'),
                selected_value_item = [];
            if (selected_value) {
                selected_value_item = {label: selected_value, value: selected_value};
            }
            if (_.find(data, function (item) {
                    return item.value === selected_value_item.value;
                }) === undefined) {
                data = data.concat(selected_value_item);
            }
            return data;
        }
    });
});
