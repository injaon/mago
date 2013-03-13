"""It support transaction using the two-steps commit """
import mago.model
from bson.objectid import ObjectId

class Transaction(mago.model.Model):
    def __init__(self, **kwargs):
        mago.model.Model.__init__(self, **kwargs)
        if self.get('new', None) is None:
            self['new'] = {}                  # coll => [mdoel]
        if self.get('del', None) is None:
            self['del'] = {}                  # coll => [id]
        if self.get('update', None) is None:
            self['update'] = {}               # coll => [min_model]
        if self.get('state', None) is None:
            self['state'] = 'initial'

    def insert(self, model_or_sequence):
        def _insert_model(tran, model):
            if model.collection_name() not in tran['new']:
                tran['new'][model.collection_name()] = []
            tran['new'][model.collection_name()].append(model)

        if isinstance(model_or_sequence, mago.model.Model):
            _insert_model(self, model_or_sequence)
        else:
            for model in model_or_sequence:
                _insert_model(self, model)


    def update(self, model_or_sequence):
        def _update_model(tran, model):
            if model.collection_name() not in tran['update']:
                tran['update'][model.collection_name()] = []
            tran['update'][model.collection_name()].append(model)

        if isinstance(model_or_sequence, mago.model.Model):
            _update_model(self, model_or_sequence)
        else:
            for model in model_or_sequence:
                _update_model(self, model)

    def remove(self, model_or_sequence):
        def _delete_model(tran, model):
            if model.collection not in tran['del']:
                tran['del'][model.collection_name()] = []
            tran['del'][model.collection_name()].append(model.id)

        if isinstance(model_or_sequence, mago.model.Model):
            _delete_model(self, model_or_sequence)
        else:
            for model in model_or_sequence:
                _delete_model(self, model)

    def _to_pending(self):
        self['state'] = 'pending'
        self.sync()

        for coll in self['new'].values():
            for model in coll:
                if self.id in model['_trans']:
                    continue
                model['_trans'].append(self.id)
                model.save()

        for coll, ids in self['del'].items():
            model_class = mago.types.models[coll]
            for model_id in ids:
                # TODO: If it was already remove?
                model_class.collection().remove({"_id": model_id})

        for coll in self['update'].values():
            for model in coll:
                if self.id in model['_trans']:
                    continue
                model['_trans'].append(self.id)
                model.sync()

    def _to_commit(self):
        self['state'] = 'commit'
        self.sync()

        for coll in self['new'].values():
            for model in coll:
                model['_trans'].remove(self.id)
                model.sync()

        for coll in self['update'].values():
            for model in coll:
                model['_trans'].remove(self.id)
                model.sync()

        self['state'] = 'finished'
        self.sync()

    def commit(self):
        try:
            self.save()
            self._to_pending()
            self._to_commit()
            self.delete()
            # TODO: Find out what exceptions are raised
        except:
            # something wring happend
            self.rollback()
            raise IOError("Rollback!")

    def rollback(self):
        # delete new documents
        for coll, models in self["new"]:
            model_class = mago.types.models[coll]
            for model in models:
                model['_trans'].pop(self.id, None)
                model_class.collection().remove({"_id", model.id})

        for models in self['del'].values():
            for model in models:
                model["_trans"].pop(self.id, None)
                model.sync()            # TODO: check it!

        for models in self['update'].values():
            for model in models:
                model['_trans'].pop(self.id, None)
                model.sync()
        self.delete()

    def recover(self):
        if self['state'] == 'initial' or self['state'] == 'pending':
            self._to_pending()

        if self['state'] == 'pending' or self['state'] == 'commit':
            self._to_commit()

        if self['state'] == 'finished':
            self.delete()


def recovery():
    Transaction.collection().remove({"state" : "finished"})
    trans = Transaction.find()
    for t in trans:
        for oper in t:
            if not  oper in ('new', 'update', 'del'):
                continue

            for coll, docs in t[oper].items():
                model_class = mago.types.models[coll]

                models = list()
                for doc_or_oid in docs:
                    if type(doc_or_oid) is ObjectId:
                        models.append(doc_or_oid)
                        continue
                    models.append(model_class(**doc_or_oid))
                t[oper][coll] = models

        t.recover()
