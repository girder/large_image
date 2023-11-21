const authOptions = [
    {
        // HTML can't accept null, but it can accept an empty string
        value: '',
        label: 'None'
    },
    {
        value: 'token',
        label: 'Token'
    }
];

export default authOptions;
