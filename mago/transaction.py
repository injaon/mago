"""It support transaction using the two-steps commit """
import mago.model


class Transaction(mago.model.Model):
    def __init__(self):
        mago.model.Model.__init__(self)
        self['new'] = {}                  # coll => [mdoel]
        self['del'] = {}                  # coll => [id]
        self['update'] = {}               # coll => [min_model]
        self['state'] = 'initial'

    def insert(self, model_or_sequence):
        try:
            for model in model_or_sequence:
                self._insert_model(model)

        except TypeError:
            self._insert_model(model_or_sequence)

    def _insert_model(self, model):
        if model.collection_name() not in self['new']:
            self['new'][model.collection_name()] = []
        self['new'][model.collection_name()].append(model)

    def update(self, model_or_sequence):
        try:
            for model in model_or_sequence:
                self._update_model(model)

        except TypeError:
            self._udpate_model(model_or_sequence)

    def _update_model(self, model):
        if model.collection_name() not in self['update']:
            self['update'][model.collection_name()] = []
        self['update'][model.collection_name()].append(model)

    def remove(self, model_or_sequence):
        try:
            for model in model_or_sequence:
                self._delete_model(model)

        except TypeError:
            self._delete_model(model_or_sequence)

    def _delete_model(self, model):
        if model.collection not in self['del']:
            self['del'][model.collection_name()] = []
        self['del'][model.collection_name()].append(model.id)

    def _to_pending(self):
        self['state'] = 'pending'
        self.sync()

        for coll in self['new'].values():
            for model in coll:
                model['_trans'] = [self.id]
                model.save()

        for coll in self['del'].values():
            for model in coll:
                model.delete()

        for coll in self['update'].values():
            for model in coll:
                model['_trans'] = [self.id]
                model.sync()

    def _to_commit(self):
        self['state'] = 'commit'
        self.sync()

        for models in self['new'].values():
            for model in models:
                model['_trans'].remove(self.id)
                model.sync()

        for models in self['update'].values():
            for model in models:
                model['_trans'].remove(self.id)
                model.sync()

    def commit(self):
        self.save()
        self._to_pending()
        self._to_commit()
        self.delete()

# TODO: recovery
